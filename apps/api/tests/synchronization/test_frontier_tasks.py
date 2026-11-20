from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from api.worker.tasks import frontier as frontier_tasks


@pytest.mark.asyncio
async def test_probe_preserves_provider_namespaces_and_seed_floors(monkeypatch):
    session = object()

    @asynccontextmanager
    async def scope():
        yield session

    monkeypatch.setattr(frontier_tasks, "session_scope", scope)
    monkeypatch.setenv("MAL_MAX_ANIME_ID", "100")
    monkeypatch.setenv("PROVIDER_FRONTIER_PROBE_WINDOW", "20")
    monkeypatch.setenv("PROVIDER_FRONTIER_MAX_MISSES", "3")
    monkeypatch.setattr(
        frontier_tasks.frontier, "highest_stored_id", AsyncMock(side_effect=[50, 200])
    )
    probe = AsyncMock(side_effect=[{"provider": "mal"}, {"provider": "bangumi"}])
    monkeypatch.setattr(frontier_tasks.frontier, "probe_frontier", probe)
    for name in ("mark_running", "mark_succeeded", "mark_failed"):
        monkeypatch.setattr(frontier_tasks.jobs, name, AsyncMock())
    result = await frontier_tasks.probe_frontiers(None, "test-worker")
    assert result == {"frontiers": [{"provider": "mal"}, {"provider": "bangumi"}]}
    calls = [call.kwargs for call in probe.await_args_list]
    assert [(c["provider_slug"], c["namespace_slug"], c["seed"]) for c in calls] == [
        ("mal", "anime", 100),
        ("bangumi", "subject", 200),
    ]
    assert all(c["window"] == 20 and c["max_misses"] == 3 for c in calls)
    frontier_tasks.jobs.mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_claimed_job_skips_provider_requests(monkeypatch):
    @asynccontextmanager
    async def scope():
        yield object()

    monkeypatch.setattr(frontier_tasks, "session_scope", scope)
    monkeypatch.setattr(frontier_tasks.jobs, "claim", AsyncMock(return_value=False))
    probe = AsyncMock()
    monkeypatch.setattr(frontier_tasks.frontier, "probe_frontier", probe)
    result = await frontier_tasks.probe_frontiers("job", "other-worker")
    assert result["skipped"] is True
    probe.assert_not_awaited()


def test_task_is_registered_on_the_worker_application():
    from api.worker.app import app

    task = app.tasks["apps.sync.tasks.frontier.probe_provider_frontiers_task"]
    assert task.queue == "sync"
    assert task.time_limit == 1900
