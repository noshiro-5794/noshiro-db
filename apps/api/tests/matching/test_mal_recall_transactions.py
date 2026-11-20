from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from api.contexts.knowledge import agent_loop, retrieval
from api.contexts.matching import mal_recall
from api.db import fetch
from api.shared import inference
from api.shared.ai import AgentCompletion, AgentToolCall
from api.worker import calendar_write, mal_import, provider_search, subject_import


def answer(content="", calls=None):
    return AgentCompletion(
        content, "fast-model", {"input_tokens": 12, "output_tokens": 8}, calls or []
    )


@pytest.fixture
async def recall_runtime(integration_session, register_provider, monkeypatch):
    await register_provider("mal", "MyAnimeList")
    await register_provider("bangumi", "Bangumi")
    session = integration_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    for module in [mal_recall, agent_loop, retrieval, inference, provider_search]:
        monkeypatch.setattr(module, "session_scope", scope)
    root = await subject_import.import_subject(session, {"id": 1, "type": 2, "name": "Anime"})
    await session.commit()
    client = Mock()
    client.search_anime.return_value = {"data": [{"node": {"id": 42, "title": "Anime"}}]}
    client.fetch_anime.return_value = {"id": 42, "title": "Anime", "media_type": "tv"}
    for module in [mal_recall, retrieval]:
        monkeypatch.setattr(module, "MALClient", lambda: client)

    async def response(**kwargs):
        if kwargs["messages"][-1]["role"] == "user":
            return answer(calls=[AgentToolCall("search", "mal.search_anime", {"query": "Anime"})])
        return answer('{"decision":"found","mal_id":42,"confidence":0.95,"reason":"Same work"}')

    model = AsyncMock(side_effect=response)
    monkeypatch.setattr(agent_loop, "complete_agent", model)
    sender = Mock(return_value="evaluation")
    monkeypatch.setattr(mal_recall, "publish", sender)
    return session, root, client, model, sender


async def board_entries(session, roots, provider="bangumi"):
    board = await calendar_write.create_board(
        session, season_key="2026Q4", observation_id=None, item_count=len(roots)
    )
    for root in roots:
        await fetch(
            session,
            "INSERT INTO airing_board_entry "
            "(id,board_id,work_id,weekday,timezone,precision,status,decision,confidence,"
            "source_refs,region,created_at,updated_at) VALUES "
            "(gen_random_uuid(),:board,:work,1,'Asia/Shanghai','weekday','ready','accepted',1,"
            "jsonb_build_array(jsonb_build_object('provider',CAST(:provider AS text))),"
            "'',now(),now()) "
            "RETURNING id",
            {"board": board, "work": root, "provider": provider},
        )
    await session.commit()


@pytest.mark.asyncio
async def test_recall_creates_pending_candidate_evidence_and_replay_is_free(recall_runtime):
    session, root, client, model, sender = recall_runtime
    result = await mal_recall.recall_one(root)
    assert result["outcome"] == "candidate_created", result
    assert result["evaluation_dispatched"] is True
    candidate = (await fetch(session, "SELECT * FROM match_candidate", {}))[0]
    assert candidate.status == "pending" and str(candidate.score) == "0.9500"
    evidence = (await fetch(session, "SELECT * FROM match_evidence", {}))[0]
    assert evidence.evidence_type == "agent_mal_recall" and evidence.value == {
        "provider_pair": "bangumi:mal",
        "mal_id": 42,
        "reason": "Same work",
        "policy_version": "mal-agent-recall-v1",
    }
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_redirect", {}))[0].n == 0
    again = await mal_recall.recall_one(root)
    assert again["outcome"] == "skipped_existing"
    assert model.await_count == 2
    client.fetch_anime.assert_called_once_with(42)
    sender.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output,outcome",
    [
        ('{"decision":"not_found","reason":"Missing"}', "not_found"),
        ('{"decision":"found","mal_id":42,"confidence":0.5}', "low_confidence"),
        ('{"decision":"found","mal_id":999,"confidence":1}', "not_found"),
        ('{"decision":"found","confidence":1}', "not_found"),
    ],
)
async def test_abstention_low_confidence_and_unobserved_ids_never_import(
    recall_runtime, output, outcome
):
    session, root, client, model, sender = recall_runtime
    model.side_effect = [
        answer(calls=[AgentToolCall("search", "mal.search_anime", {"query": "Anime"})]),
        answer(output),
    ]
    result = await mal_recall.recall_one(root)
    assert result["outcome"] == outcome, result
    client.fetch_anime.assert_not_called()
    sender.assert_not_called()
    assert (await fetch(session, "SELECT count(*) AS n FROM match_candidate", {}))[0].n == 0


@pytest.mark.asyncio
async def test_existing_mal_identity_is_reused_without_fetch(recall_runtime):
    session, root, client, _, _ = recall_runtime
    await mal_import.import_anime(session, {"id": 42, "title": "Imported"})
    await session.commit()
    result = await mal_recall.recall_one(root, evaluate=False)
    assert result["outcome"] == "candidate_created", result
    client.fetch_anime.assert_not_called()
    assert "evaluation_dispatched" not in result


@pytest.mark.asyncio
async def test_import_failure_retries_saved_decision_without_paying_for_another_model(
    recall_runtime,
):
    session, root, client, model, _ = recall_runtime
    client.fetch_anime.side_effect = RuntimeError("MAL unavailable")
    failed = await mal_recall.recall_one(root)
    assert failed["outcome"] == "failed"
    assert (await fetch(session, "SELECT status FROM agent_run", {}))[0].status == "succeeded"
    client.fetch_anime.side_effect = None
    retried = await mal_recall.recall_one(root)
    assert retried["outcome"] == "candidate_created", retried
    assert model.await_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_run", {}))[0].n == 1


@pytest.mark.asyncio
async def test_candidate_evidence_failure_rolls_back_import_and_retries_saved_decision(
    recall_runtime, monkeypatch
):
    session, root, _, model, _ = recall_runtime
    real_fetch = mal_recall.fetch

    async def fail_evidence(session, query, parameters):
        if query.startswith("INSERT INTO match_evidence"):
            raise RuntimeError("Evidence failed")
        return await real_fetch(session, query, parameters)

    monkeypatch.setattr(mal_recall, "fetch", fail_evidence)
    failed = await mal_recall.recall_one(root)
    assert failed["outcome"] == "failed"
    assert (await fetch(session, "SELECT count(*) AS n FROM match_candidate", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 1
    monkeypatch.setattr(mal_recall, "fetch", real_fetch)
    retried = await mal_recall.recall_one(root)
    assert retried["outcome"] == "candidate_created", retried
    assert model.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["running", "paused", "waiting"])
async def test_inflight_attempt_is_preserved_even_with_force(recall_runtime, status):
    session, root, client, model, _ = recall_runtime
    identifier = await mal_recall.prepare(root, force=False)
    await fetch(
        session,
        "UPDATE agent_run SET status=:status WHERE id=:id RETURNING id",
        {"id": identifier, "status": status},
    )
    await session.commit()
    result = await mal_recall.recall_one(root, force=True)
    assert result["outcome"] == status
    model.assert_not_awaited()
    client.fetch_anime.assert_not_called()


@pytest.mark.asyncio
async def test_stale_running_attempt_is_recovered_in_place(recall_runtime):
    session, root, _, model, _ = recall_runtime
    identifier = await mal_recall.prepare(root, force=False)
    await fetch(
        session,
        "UPDATE agent_run SET status='running',updated_at=now()-interval '2 hours' "
        "WHERE id=:id RETURNING id",
        {"id": identifier},
    )
    await session.commit()
    result = await mal_recall.recall_one(root)
    assert result["outcome"] == "candidate_created", result
    assert model.await_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_run", {}))[0].n == 1


@pytest.mark.asyncio
async def test_force_retains_prior_audit_and_creates_a_new_attempt(recall_runtime):
    session, root, client, model, _ = recall_runtime
    await mal_recall.recall_one(root, evaluate=False)
    result = await mal_recall.recall_one(root, force=True, evaluate=False)
    assert result["outcome"] == "candidate_created", result
    assert model.await_count == 4
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_run", {}))[0].n == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM match_evidence", {}))[0].n == 1
    client.fetch_anime.assert_called_once()


@pytest.mark.asyncio
async def test_board_walk_skips_concluded_roots_without_spending_limit(recall_runtime):
    session, root, _, model, _ = recall_runtime
    other = await subject_import.import_subject(session, {"id": 2, "type": 2, "name": "Other"})
    await session.commit()
    await board_entries(session, [root, other])
    model.side_effect = [answer('{"decision":"not_found"}'), answer('{"decision":"not_found"}')]
    await mal_recall.recall_one(root)
    result = await mal_recall.run_missing(limit=1)
    assert result["processed"] == 1, result
    assert result["results"][0]["root_entity_id"] == str(other)


@pytest.mark.asyncio
async def test_board_pending_candidates_and_other_provider_entries_are_skipped(recall_runtime):
    session, root, _, model, _ = recall_runtime
    await board_entries(session, [root])
    await mal_recall.recall_one(root)
    before = model.await_count
    result = await mal_recall.run_missing(force=True)
    assert result["processed"] == 0 and model.await_count == before
    await fetch(session, "DELETE FROM match_candidate RETURNING id", {})
    await fetch(
        session,
        "UPDATE airing_board_entry SET source_refs="
        "jsonb_build_array(jsonb_build_object('provider','mal')) RETURNING id",
        {},
    )
    await session.commit()
    result = await mal_recall.run_missing(force=True)
    assert result["processed"] == 0 and model.await_count == before


@pytest.mark.asyncio
async def test_pause_during_import_rejects_late_projection(recall_runtime):
    session, root, client, _, _ = recall_runtime
    real_fetch = mal_recall.fetch_anime

    async def paused(projection, mal_id):
        payload = await real_fetch(projection, mal_id)
        await fetch(
            session,
            "UPDATE agent_run SET status='paused',updated_at=clock_timestamp() RETURNING id",
            {},
        )
        await session.commit()
        return payload

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(mal_recall, "fetch_anime", paused)
        result = await mal_recall.recall_one(root)
    assert result["outcome"] == "paused", result
    client.fetch_anime.assert_called_once()
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 1


@pytest.mark.asyncio
async def test_broker_failure_retains_pending_candidate_for_existing_dispatch_sweep(recall_runtime):
    session, root, _, _, sender = recall_runtime
    sender.side_effect = RuntimeError("Broker unavailable")
    result = await mal_recall.recall_one(root)
    assert result["outcome"] == "candidate_created" and result["evaluation_dispatched"] is False
    assert (await fetch(session, "SELECT status FROM match_candidate", {}))[0].status == "pending"
