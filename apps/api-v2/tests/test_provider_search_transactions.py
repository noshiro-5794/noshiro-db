from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest

from api.contexts.knowledge import agent_runs
from api.contexts.presentation.fragments import fetch
from api.worker import provider_search
from api.worker.providers.errors import ProviderError


@pytest.fixture
async def search_runtime(bangumi_session, monkeypatch):
    session = bangumi_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    monkeypatch.setattr(provider_search, "session_scope", scope)
    client = Mock()
    client.search_subjects.return_value = {
        "data": [{"id": 42, "name": "Anime", "summary": "x" * 1000, "images": {"large": "cover"}}],
        "total": 1,
    }
    monkeypatch.setattr(provider_search, "BangumiClient", lambda: client)
    identifier = await agent_runs.create_run(
        session,
        title="Search",
        scope="test-search",
        key="1",
        metadata={"scopes": ["bangumi:search"]},
    )
    await fetch(
        session,
        "UPDATE agent_run SET status='running' WHERE id=:id RETURNING id",
        {"id": identifier},
    )
    await session.commit()
    return session, identifier, client


@pytest.mark.asyncio
async def test_search_persists_owned_artifact_and_per_attempt_audit(search_runtime):
    session, identifier, client = search_runtime
    result = await provider_search.search_bangumi("Anime", run_id=identifier)
    assert result.available is True and result.results[0]["id"] == 42
    assert len(result.results[0]["summary"]) == 800
    rows = await fetch(
        session,
        "SELECT s.run_id,t.status,a.excerpt,a.metadata FROM source_artifact a "
        "JOIN tool_invocation t ON t.id=a.tool_invocation_id JOIN agent_step s ON s.id=t.step_id",
        {},
    )
    assert rows[0].run_id == identifier and rows[0].status == "succeeded"
    assert rows[0].metadata == {
        "query": "Anime",
        "tool_name": "bangumi.search_subjects",
        "tool_version": "1.0.0",
    }
    await provider_search.search_bangumi("Anime", run_id=identifier)
    assert (await fetch(session, "SELECT count(*) AS n FROM tool_invocation", {}))[0].n == 2
    assert client.close.call_count == 2


@pytest.mark.asyncio
async def test_unavailable_search_records_failure_and_can_be_retried(search_runtime):
    session, identifier, client = search_runtime
    client.search_subjects.side_effect = ProviderError("Unavailable", status_code=503)
    result = await provider_search.search_bangumi("Anime", run_id=identifier)
    assert result.available is False
    assert (await fetch(session, "SELECT status FROM tool_invocation", {}))[0].status == "failed"
    client.search_subjects.side_effect = None
    retried = await provider_search.search_bangumi("Anime", run_id=identifier)
    assert retried.available is True
    assert (await fetch(session, "SELECT count(*) AS n FROM tool_invocation", {}))[0].n == 2


@pytest.mark.asyncio
async def test_scope_and_cancelled_run_block_provider_access(search_runtime):
    session, identifier, client = search_runtime
    await fetch(
        session, "UPDATE agent_run SET metadata='{}' WHERE id=:id RETURNING id", {"id": identifier}
    )
    await session.commit()
    with pytest.raises(PermissionError):
        await provider_search.search_bangumi("Anime", run_id=identifier)
    await fetch(
        session,
        "UPDATE agent_run SET status='cancelled' WHERE id=:id RETURNING id",
        {"id": identifier},
    )
    await session.commit()
    with pytest.raises(RuntimeError, match="not running"):
        await provider_search.search_bangumi("Anime", run_id=identifier)
    client.search_subjects.assert_not_called()
    assert (await fetch(session, "SELECT count(*) AS n FROM tool_invocation", {}))[0].n == 0


@pytest.mark.asyncio
async def test_cancellation_during_request_prevents_evidence_capture(search_runtime):
    session, identifier, _ = search_runtime

    async def cancelled():
        await fetch(
            session,
            "UPDATE agent_run SET status='cancelled' WHERE id=:id RETURNING id",
            {"id": identifier},
        )
        await session.commit()
        return provider_search.SearchResult(available=True, results=[{"id": 42}])

    with pytest.raises(RuntimeError, match="not running"):
        await provider_search.invoke(
            run_id=identifier,
            tool="bangumi.search_subjects",
            permission="bangumi:search",
            parameters={},
            handler=cancelled,
        )
    assert (await fetch(session, "SELECT count(*) AS n FROM source_artifact", {}))[0].n == 0
    assert (await fetch(session, "SELECT status FROM tool_invocation", {}))[0].status == "failed"
