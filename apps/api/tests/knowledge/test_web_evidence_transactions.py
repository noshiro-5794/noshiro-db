from unittest.mock import AsyncMock

import pytest

from api.contexts.knowledge import agent_runs, web_evidence
from api.db import fetch
from tests.knowledge.test_normalization_transactions import (
    normalization_runtime as normalization_runtime,
)

RESULT = {
    "title": "Source title",
    "url": "https://source.test/work",
    "content": "Documented work title",
    "score": 0.9,
}


@pytest.fixture
async def search_runtime(normalization_runtime, monkeypatch):
    session, context, _ = normalization_runtime
    from api.contexts.knowledge import normalization

    monkeypatch.setattr(web_evidence, "session_scope", normalization.session_scope)
    monkeypatch.setattr(web_evidence, "configured", lambda: True)
    search = AsyncMock(return_value=[RESULT])
    monkeypatch.setattr(web_evidence, "search", search)
    return session, context, search


@pytest.mark.asyncio
async def test_search_captures_content_addressed_artifact_and_reuses_identical_query(
    search_runtime,
):
    session, context, search = search_runtime
    first = await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=context.run_id)
    second = await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=context.run_id)
    assert first == second
    assert first[0].source_url == RESULT["url"]
    assert first[0].content_hash == agent_runs.payload_hash(RESULT)
    assert first[0].metadata == {
        "title": RESULT["title"],
        "score": 0.9,
        "tool_name": "web.search",
        "tool_version": "1.0.0",
    }
    search.assert_awaited_once_with("Anime", max_results=5)
    step = (await fetch(session, "SELECT kind,status,skill_name FROM agent_step", {}))[0]
    assert tuple(step) == ("tool", "succeeded", "")
    invocation = (await fetch(session, "SELECT status,result FROM tool_invocation", {}))[0]
    assert invocation.status == "succeeded"
    assert invocation.result == {"available": True, "results": [RESULT]}


@pytest.mark.asyncio
async def test_failed_search_records_terminal_audit_and_can_retry_same_entity(search_runtime):
    session, context, search = search_runtime
    search.side_effect = [RuntimeError("search unavailable"), [RESULT]]
    assert (
        await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=context.run_id) == []
    )
    artifacts = await web_evidence.gather(
        "Anime", entity_id=context.entity_id, run_id=context.run_id
    )
    assert len(artifacts) == 1
    steps = await fetch(
        session, "SELECT sequence,status,output,error FROM agent_step ORDER BY sequence", {}
    )
    assert [row.status for row in steps] == ["failed", "succeeded"]
    assert steps[0].output is None
    assert steps[0].error == "RuntimeError: search unavailable"
    assert (await fetch(session, "SELECT count(*) AS n FROM tool_invocation", {}))[0].n == 2


@pytest.mark.asyncio
async def test_expired_cache_searches_again_and_preserves_prior_artifact(search_runtime):
    session, context, search = search_runtime
    first = await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=context.run_id)
    await fetch(
        session, "UPDATE tool_invocation SET finished_at=now()-interval '31 days' RETURNING id", {}
    )
    await session.commit()
    second = await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=context.run_id)
    assert first[0].id != second[0].id
    assert first[0].content_hash == second[0].content_hash
    assert search.await_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM source_artifact", {}))[0].n == 2


@pytest.mark.asyncio
async def test_blank_query_does_not_allocate_steps_or_search(search_runtime):
    session, context, search = search_runtime
    assert (
        await web_evidence.gather("   ", entity_id=context.entity_id, run_id=context.run_id) == []
    )
    search.assert_not_awaited()
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_step", {}))[0].n == 0


@pytest.mark.asyncio
async def test_cache_is_reusable_across_agent_runs(search_runtime):
    session, context, search = search_runtime
    first = await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=context.run_id)
    other = (
        await fetch(
            session,
            """
        INSERT INTO agent_run
          (id,kind,status,title,idempotency_key,idempotency_scope,trace_id,metadata,checkpoint,
           budget,error,created_at,updated_at)
        VALUES (gen_random_uuid(),'admin_sync','queued','Other','','','','{}','{}','{}','',
                now(),now()) RETURNING id
    """,
            {},
        )
    )[0].id
    await session.commit()
    second = await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=other)
    assert first == second
    search.assert_awaited_once()
    assert (
        await fetch(session, "SELECT count(*) AS n FROM agent_step WHERE run_id=:id", {"id": other})
    )[0].n == 0


@pytest.mark.asyncio
async def test_empty_results_can_be_searched_again_without_idempotency_conflict(search_runtime):
    session, context, search = search_runtime
    search.return_value = []
    for _ in range(2):
        assert (
            await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=context.run_id)
            == []
        )
    assert search.await_count == 2
    rows = await fetch(session, "SELECT status FROM tool_invocation", {})
    assert [row.status for row in rows] == ["succeeded", "succeeded"]


@pytest.mark.asyncio
async def test_artifact_failure_rolls_back_partial_capture_and_records_failed_step(search_runtime):
    session, context, search = search_runtime
    search.return_value = [RESULT, {**RESULT, "url": "https://source.test/" + "x" * 2100}]
    assert (
        await web_evidence.gather("Anime", entity_id=context.entity_id, run_id=context.run_id) == []
    )
    assert (await fetch(session, "SELECT count(*) AS n FROM source_artifact", {}))[0].n == 0
    assert (await fetch(session, "SELECT status FROM tool_invocation", {}))[0].status == "failed"
    assert (await fetch(session, "SELECT status FROM agent_step", {}))[0].status == "failed"
