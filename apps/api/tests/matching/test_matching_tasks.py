from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from api.worker.tasks import matching as matching_tasks


@pytest.mark.asyncio
async def test_three_legs_publish_only_after_database_commit(monkeypatch):
    events = []

    @asynccontextmanager
    async def scope():
        yield object()
        events.append("committed")

    leg = {
        "window": 1,
        "skipped_processed": 0,
        "cursor_after": 1,
        "catalogue_size": 1,
        "completed_pass": False,
        "candidates_created": 1,
        "conflicting_pairs": 0,
        "created_ids": ["candidate"],
    }
    service = Mock()
    for method in (
        "generate_anime_candidates",
        "generate_mal_bangumi_candidates",
        "generate_galgame_candidates",
    ):
        setattr(service, method, AsyncMock(return_value=leg))
    monkeypatch.setattr(matching_tasks, "session_scope", scope)
    monkeypatch.setattr(matching_tasks, "ProviderCandidateService", Mock(return_value=service))

    def publish(task, kwargs, *, queue):
        assert events == ["committed"]
        assert task == matching_tasks.EVALUATE_TASK
        assert kwargs == {"candidate_id": "candidate"}
        assert queue == "ai"
        return "task-id"

    monkeypatch.setattr(matching_tasks, "publish", publish)
    result = await matching_tasks.sweep(30)
    assert result["candidates_created"] == 3
    assert result["ai_evaluations_dispatched"] == 3
    service.generate_anime_candidates.assert_awaited_once_with(limit=10)
    service.generate_mal_bangumi_candidates.assert_awaited_once_with(limit=10)
    service.generate_galgame_candidates.assert_awaited_once_with(limit=10)


def test_sweep_is_registered_on_sync_queue():
    from api.worker.app import app

    task = app.tasks["apps.sync.tasks.matching.sweep_match_candidates_task"]
    assert task.queue == "sync"
    assert task.time_limit == 5700
