from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from api.contexts.scheduling import service
from api.contexts.scheduling.domain import SlotProposal


def slot(**changes):
    return {
        "decision": "accept",
        "weekday": 1,
        "time": "23:30",
        "timezone": "Asia/Tokyo",
        "confidence": "0.9",
        "duration_minutes": 24,
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"weekday": True},
        {"weekday": 8},
        {"weekday": None},
        {"time": "25:00"},
        {"time": "23:90"},
        {"time": "9:00"},
        {"timezone": "unknown/zone"},
        {"confidence": True},
        {"confidence": "NaN"},
        {"confidence": 1.1},
        {"duration_minutes": -1},
        {"duration_minutes": True},
    ],
)
def test_invalid_schedule_is_rejected(changes):
    with pytest.raises(ValidationError):
        SlotProposal.model_validate(slot(**changes))


def test_same_day_future_slot_is_converted_to_utc():
    proposal = SlotProposal.model_validate(slot())
    assert proposal.next_occurrence(datetime(2026, 11, 16, 12, tzinfo=UTC)) == datetime(
        2026, 11, 16, 14, 30, tzinfo=UTC
    )


def test_exact_current_slot_moves_to_following_week():
    proposal = SlotProposal.model_validate(slot())
    assert proposal.next_occurrence(datetime(2026, 11, 16, 14, 30, tzinfo=UTC)) == datetime(
        2026, 11, 23, 14, 30, tzinfo=UTC
    )


def test_abstention_has_no_occurrence():
    with pytest.raises(ValueError):
        SlotProposal(decision="abstain").next_occurrence(datetime.now(UTC))


@pytest.fixture
def workflow(monkeypatch):
    @asynccontextmanager
    async def scope():
        yield object()

    monkeypatch.setattr(service, "session_scope", scope)
    entry = SimpleNamespace(
        id="entry", work_id="work", title="Title", source_refs=[], season_key="2026Q4"
    )
    monkeypatch.setattr(service, "pending_entries", AsyncMock(return_value=[entry]))
    monkeypatch.setattr(service, "configured", lambda: True)
    monkeypatch.setattr(service, "create_run", AsyncMock(return_value="run"))
    finish = AsyncMock()
    monkeypatch.setattr(service, "finish_run", finish)
    return entry, finish


@pytest.mark.asyncio
async def test_missing_search_configuration_skips_external_work(monkeypatch, workflow):
    monkeypatch.setattr(service, "configured", lambda: False)
    search = AsyncMock()
    monkeypatch.setattr(service, "search", search)
    result = await service.run()
    assert result["skipped_no_search"] == 1
    search.assert_not_awaited()
    service.create_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_search_evidence_abstains_without_model_call(monkeypatch, workflow):
    _, finish = workflow
    monkeypatch.setattr(service, "search", AsyncMock(return_value=[]))
    model = AsyncMock()
    monkeypatch.setattr(service, "complete_json", model)
    result = await service.run()
    assert result["searched"] == 1
    assert result["abstained"] == 1
    assert result["applied"] == 0
    model.assert_not_awaited()
    finish.assert_awaited_once_with("run", "succeeded")


@pytest.mark.asyncio
async def test_completion_preserves_apply_flag_and_evidence(monkeypatch, workflow):
    _entry, finish = workflow
    results = [{"url": "https://example.test/schedule", "content": "Monday 23:30"}]
    monkeypatch.setattr(service, "search", AsyncMock(return_value=results))
    artifact = object()
    capture = AsyncMock(return_value=artifact)
    monkeypatch.setattr(service, "capture_results", capture)
    monkeypatch.setattr(service, "complete_json", AsyncMock(return_value=(slot(), {})))
    persist = AsyncMock(return_value={"bucket": "accepted", "claim_id": "claim", "applied": False})
    monkeypatch.setattr(service, "persist_result", persist)
    result = await service.run(limit=1, apply=False)
    assert result["accepted"] == 1
    assert result["claims"] == ["claim"]
    assert not persist.await_args.kwargs["apply"]
    assert persist.await_args.kwargs["artifact"] is artifact
    capture.assert_awaited_once_with(results, "Title 放送 曜日 時刻 アニメ")
    finish.assert_awaited_once_with("run", "succeeded")


@pytest.mark.asyncio
async def test_model_failure_marks_durable_run_failed(monkeypatch, workflow):
    _, finish = workflow
    monkeypatch.setattr(
        service, "search", AsyncMock(return_value=[{"url": "https://example.test"}])
    )
    monkeypatch.setattr(service, "capture_results", AsyncMock(return_value=object()))
    monkeypatch.setattr(
        service, "complete_json", AsyncMock(side_effect=RuntimeError("model failed"))
    )
    with pytest.raises(RuntimeError):
        await service.run()
    finish.assert_awaited_once_with("run", "failed")


def test_schedule_task_retains_its_retry_and_time_limits():
    from api.worker.app import app

    task = app.tasks["apps.ai.tasks.complete_missing_schedule_slots_task"]
    assert task.queue == "ai"
    assert task.max_retries == 2
    assert task.time_limit == 700


def test_schedule_payload_preserves_numeric_confidence():
    payload = SlotProposal.model_validate(slot()).model_dump(mode="json")
    assert payload["confidence"] == 0.9
    assert isinstance(payload["confidence"], float)
