from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from api.contexts.index import resolution
from api.contexts.matching import bangumi_link
from api.db import fetch
from api.integrations.providers.errors import ProviderError
from api.shared import inference
from api.worker import mal_import, provider_search


@pytest.fixture
async def link_runtime(integration_session, register_provider, monkeypatch):
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

    for module in [bangumi_link, provider_search, inference]:
        monkeypatch.setattr(module, "session_scope", scope)
    root = await mal_import.import_anime(session, {"id": 1, "title": "Anime", "media_type": "tv"})
    await session.commit()
    client = Mock()
    client.search_subjects.return_value = {
        "data": [{"id": 42, "name": "Anime", "date": "2026-01-01"}],
        "total": 1,
    }
    client.fetch_subject.return_value = {"id": 42, "type": 2, "name": "Anime"}
    client.fetch_subject_episodes.return_value = {"data": []}
    for module in [bangumi_link, provider_search]:
        monkeypatch.setattr(module, "BangumiClient", lambda: client)
    model = AsyncMock(
        return_value=(
            {"decision": "found", "subject_id": 42, "confidence": 0.95, "reason": "Same work"},
            {"input_tokens": 12, "output_tokens": 8},
        )
    )
    monkeypatch.setattr(bangumi_link, "complete_json", model)
    return session, root, client, model


@pytest.mark.asyncio
async def test_high_confidence_link_is_reviewable_and_replay_is_a_noop(link_runtime):
    session, root, client, model = link_runtime
    result = await bangumi_link.attempt(root)
    assert result["outcome"] == "candidate_pending", result.get("error", result)
    candidate = (await fetch(session, "SELECT * FROM match_candidate", {}))[0]
    assert candidate.status == "pending"
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_identity_membership", {}))[
        0
    ].n == 0
    audit = await fetch(session, "SELECT status,metadata FROM agent_run", {})
    assert audit[0].status == "succeeded" and audit[0].metadata["episodes_synced"] is True
    replay = await bangumi_link.attempt(root)
    assert replay["outcome"] == "skipped_existing"
    assert replay["attempt_id"] == str((await fetch(session, "SELECT id FROM agent_run", {}))[0].id)
    model.assert_awaited_once()
    client.search_subjects.assert_called_once()
    assert (await fetch(session, "SELECT count(*) AS n FROM source_artifact", {}))[0].n == 2


@pytest.mark.asyncio
async def test_explicit_application_uses_resolution_and_retains_candidate_audit(link_runtime):
    session, root, _, _ = link_runtime
    result = await bangumi_link.attempt(root, apply=True)
    assert result["outcome"] == "linked"
    assert (await fetch(session, "SELECT status FROM match_candidate", {}))[0].status == "accepted"
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_merge_event", {}))[0].n == 1
    assert await resolution.resolve(session, root) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "decision",
    [
        {"decision": "found", "subject_id": 999, "confidence": 1},
        {"decision": "found", "subject_id": 42, "confidence": 0.5},
        {"decision": "not_found", "subject_id": 42, "confidence": 0.9},
    ],
)
async def test_unproven_or_low_confidence_id_never_imports(link_runtime, decision):
    session, root, client, model = link_runtime
    model.return_value = (decision, {})
    result = await bangumi_link.attempt(root)
    assert result["outcome"] == "abstained"
    client.fetch_subject.assert_not_called()
    assert (await fetch(session, "SELECT count(*) AS n FROM match_candidate", {}))[0].n == 0


@pytest.mark.asyncio
async def test_search_outage_retries_failed_attempt_without_duplicate_run(link_runtime):
    session, root, client, model = link_runtime
    client.search_subjects.side_effect = ProviderError("Unavailable", status_code=503)
    failed = await bangumi_link.attempt(root)
    assert failed["outcome"] == "failed"
    model.assert_not_awaited()
    client.search_subjects.side_effect = None
    retried = await bangumi_link.attempt(root)
    assert retried["outcome"] == "candidate_pending"
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_run", {}))[0].n == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM tool_invocation", {}))[0].n == 2


@pytest.mark.asyncio
async def test_no_search_hits_conclude_without_model_or_import(link_runtime):
    _, root, client, model = link_runtime
    client.search_subjects.return_value = {"data": []}
    result = await bangumi_link.attempt(root)
    assert result["outcome"] == "no_match"
    model.assert_not_awaited()
    client.fetch_subject.assert_not_called()


@pytest.mark.asyncio
async def test_episode_outage_keeps_subject_and_pending_candidate(link_runtime):
    session, root, client, _ = link_runtime
    client.fetch_subject_episodes.side_effect = ProviderError("Unavailable", status_code=503)
    result = await bangumi_link.attempt(root)
    assert result["outcome"] == "candidate_pending"
    assert (await fetch(session, "SELECT metadata FROM agent_run", {}))[0].metadata[
        "episodes_synced"
    ] is False


@pytest.mark.asyncio
async def test_model_contract_failure_persists_failed_step_and_inference(link_runtime):
    session, root, _, model = link_runtime
    model.return_value = ({"decision": "invented", "confidence": 1}, {})
    result = await bangumi_link.attempt(root)
    assert result["outcome"] == "failed"
    assert (await fetch(session, "SELECT status FROM ai_run", {}))[0].status == "failed"
    assert (await fetch(session, "SELECT status FROM agent_step WHERE kind='model'", {}))[
        0
    ].status == "failed"


@pytest.mark.asyncio
async def test_paused_attempt_rejects_late_model_result_without_canonical_writes(link_runtime):
    session, root, client, model = link_runtime

    async def paused(**kwargs):
        await fetch(
            session,
            "UPDATE agent_run SET status='paused',updated_at=clock_timestamp() RETURNING id",
            {},
        )
        await session.commit()
        return {"decision": "found", "subject_id": 42, "confidence": 0.95}, {}

    model.side_effect = paused
    result = await bangumi_link.attempt(root)
    assert result["outcome"] == "paused"
    client.fetch_subject.assert_not_called()
    assert (await fetch(session, "SELECT count(*) AS n FROM match_candidate", {}))[0].n == 0


@pytest.mark.asyncio
async def test_force_repeats_concluded_attempt_and_preserves_one_run(link_runtime):
    session, root, client, _ = link_runtime
    client.search_subjects.return_value = {"data": []}
    first = await bangumi_link.attempt(root)
    second = await bangumi_link.attempt(root, force=True)
    assert first["attempt_id"] == second["attempt_id"]
    assert client.search_subjects.call_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_run", {}))[0].n == 1


@pytest.mark.asyncio
async def test_active_attempt_is_not_restarted_even_with_force(link_runtime):
    _session, root, client, _ = link_runtime
    prepared = await bangumi_link.prepare(root, force=False)
    result = await bangumi_link.attempt(root, force=True)
    assert result["outcome"] == "already_running" and result["attempt_id"] == str(prepared.run_id)
    client.search_subjects.assert_not_called()


@pytest.mark.asyncio
async def test_concluded_roots_do_not_spend_actionable_walk_limit(link_runtime):
    session, root, client, _ = link_runtime
    other = await mal_import.import_anime(session, {"id": 2, "title": "Other", "media_type": "tv"})
    await session.commit()
    roots = sorted([root, other], key=str)
    client.search_subjects.return_value = {"data": []}
    await bangumi_link.attempt(roots[0])
    result = await bangumi_link.run_missing(limit=1)
    assert result["scanned"] == 2 and result["processed"] == 1
    assert result["results"][0]["root_entity_id"] == str(roots[1])
    assert client.search_subjects.call_count == 2


@pytest.mark.asyncio
async def test_refused_bind_is_audited_as_abstained(link_runtime, monkeypatch):
    session, root, _, _ = link_runtime
    real_decide = resolution.decide

    async def refused(session, **kwargs):
        if kwargs["outcome"] == "bind":
            raise resolution.ResolutionError("Incompatible identity")
        return await real_decide(session, **kwargs)

    monkeypatch.setattr(resolution, "decide", refused)
    result = await bangumi_link.attempt(root, apply=True)
    assert result["outcome"] == "abstained"
    assert (await fetch(session, "SELECT status FROM match_candidate", {}))[0].status == "abstained"
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_identity_membership", {}))[
        0
    ].n == 0


@pytest.mark.asyncio
async def test_evidence_failure_rolls_back_candidate_and_retry_reuses_import(
    link_runtime, monkeypatch
):
    session, root, _, _ = link_runtime
    real_fetch = bangumi_link.fetch

    async def fail_evidence(session, query, parameters):
        if query.startswith("INSERT INTO match_evidence"):
            raise RuntimeError("Evidence write failed")
        return await real_fetch(session, query, parameters)

    monkeypatch.setattr(bangumi_link, "fetch", fail_evidence)
    failed = await bangumi_link.attempt(root)
    assert failed["outcome"] == "failed"
    assert (await fetch(session, "SELECT count(*) AS n FROM match_candidate", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 2
    monkeypatch.setattr(bangumi_link, "fetch", real_fetch)
    retried = await bangumi_link.attempt(root)
    assert retried["outcome"] == "candidate_pending"
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 2


@pytest.mark.asyncio
async def test_stale_running_attempt_recovers_inflight_audit_and_rejects_old_writer(link_runtime):
    from api.contexts.knowledge import agent_runs

    session, root, client, _ = link_runtime
    previous = await bangumi_link.prepare(root, force=False)
    step = await agent_runs.create_step(
        session, run_id=previous.run_id, skill="", payload={}, kind="model"
    )
    await session.commit()
    ai_run = await inference.start_run(
        payload={},
        use_case="bangumi_link_search",
        prompt_version="test",
        metadata={},
        agent_step_id=step,
    )
    await fetch(
        session,
        "UPDATE agent_run SET updated_at=clock_timestamp()-interval '2 hours' "
        "WHERE id=:id RETURNING id",
        {"id": previous.run_id},
    )
    await session.commit()
    reclaimed = await bangumi_link.prepare(root, force=False)
    assert reclaimed.run_id == previous.run_id and reclaimed.version != previous.version
    assert (await fetch(session, "SELECT status FROM agent_step WHERE id=:id", {"id": step}))[
        0
    ].status == "failed"
    assert (await fetch(session, "SELECT status FROM ai_run WHERE id=:id", {"id": ai_run}))[
        0
    ].status == "failed"
    with pytest.raises(bangumi_link.AttemptStopped):
        await bangumi_link.own(session, previous)
    await bangumi_link.finish(reclaimed, "no_match", {})
    client.search_subjects.assert_not_called()
