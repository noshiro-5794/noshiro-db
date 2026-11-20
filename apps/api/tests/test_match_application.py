from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.contexts.matching import batch


def proposal(**changes):
    return SimpleNamespace(
        proposal_id="proposal",
        candidate_id="candidate",
        payload={"decision": "bind"},
        confidence=Decimal("0.97"),
        score=Decimal("1"),
        hard_conflicts=[],
        left_entity_id="left",
        right_entity_id="right",
        left_kind="work",
        right_kind="work",
        **changes,
    )


@pytest.mark.asyncio
async def test_all_batch_gates_report_the_legacy_reasons(monkeypatch):
    value = proposal()
    value.payload = {"decision": "abstain"}
    value.confidence = Decimal("0.5")
    value.score = Decimal("0.9")
    value.hard_conflicts = [{}]
    value.right_kind = "character"
    monkeypatch.setattr(
        batch.resolution, "cluster_ids", AsyncMock(side_effect=[{"left"}, {"right"}])
    )
    monkeypatch.setattr(
        batch,
        "fetch",
        AsyncMock(
            side_effect=[
                [
                    SimpleNamespace(entity_id="left", work_type="anime"),
                    SimpleNamespace(entity_id="right", work_type="galgame"),
                ],
                [
                    SimpleNamespace(premiered_on=date(2001, 1, 1)),
                    SimpleNamespace(premiered_on=date(2021, 1, 1)),
                ],
                [object()],
            ]
        ),
    )
    assert await batch.gate_reasons(object(), value) == [
        "ai_decision='abstain'",
        "confidence_below_threshold",
        "candidate_score_below_threshold",
        "hard_conflicts",
        "entity_kind_mismatch",
        "work_family_mismatch",
        "release_year_conflict",
        "conflicting_user_library",
    ]


@pytest.mark.asyncio
async def test_dry_run_wraps_without_writing_cursor(monkeypatch):
    query = AsyncMock(return_value=[SimpleNamespace(current_id=10)])
    monkeypatch.setattr(batch, "fetch", query)
    window = AsyncMock(side_effect=[([], 2), ([proposal()], 2)])
    monkeypatch.setattr(batch, "read_window", window)
    monkeypatch.setattr(batch, "gate_reasons", AsyncMock(return_value=[]))
    result = await batch.apply_proposals(object(), limit=1)
    assert result["completed_pass"]
    assert result["cursor_before"] == result["cursor_after"] == 0
    assert result["would_bind"] == 1
    assert result["accepted"] == 0
    query.assert_awaited_once()


@pytest.mark.asyncio
async def test_deferred_window_advances_by_survivors(monkeypatch):
    query = AsyncMock(side_effect=[[], [SimpleNamespace(total=1)], []])
    monkeypatch.setattr(batch, "fetch", query)
    monkeypatch.setattr(batch, "read_window", AsyncMock(return_value=([proposal()], 3)))
    monkeypatch.setattr(
        batch, "gate_reasons", AsyncMock(return_value=["confidence_below_threshold"])
    )
    result = await batch.apply_proposals(
        SimpleNamespace(execute=AsyncMock()), apply=True, abstain_ineligible=False
    )
    assert result["deferred"] == 1
    assert result["cursor_after"] == 1
    assert query.await_args.args[2]["cursor"] == 1


@pytest.mark.asyncio
async def test_failure_in_one_proposal_does_not_abort_following_proposal(monkeypatch):
    @asynccontextmanager
    async def savepoint():
        yield

    session = SimpleNamespace(execute=AsyncMock(), begin_nested=savepoint)
    monkeypatch.setattr(batch, "fetch", AsyncMock(side_effect=[[], [SimpleNamespace(total=1)], []]))
    monkeypatch.setattr(batch, "read_window", AsyncMock(return_value=([proposal(), proposal()], 2)))
    monkeypatch.setattr(batch, "gate_reasons", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        batch, "decide", AsyncMock(side_effect=[RuntimeError("failed pair"), "accepted"])
    )
    result = await batch.apply_proposals(session, apply=True)
    assert result["accepted"] == 1
    assert result["errors"] == [{"proposal_id": "proposal", "error": "failed pair"}]


@pytest.mark.asyncio
async def test_concurrent_decision_is_not_reported_as_a_new_acceptance(monkeypatch):
    @asynccontextmanager
    async def savepoint():
        yield

    session = SimpleNamespace(execute=AsyncMock(), begin_nested=savepoint)
    monkeypatch.setattr(batch, "fetch", AsyncMock(side_effect=[[], [SimpleNamespace(total=0)], []]))
    monkeypatch.setattr(batch, "read_window", AsyncMock(return_value=([proposal()], 1)))
    monkeypatch.setattr(batch, "gate_reasons", AsyncMock(return_value=[]))
    monkeypatch.setattr(batch, "decide", AsyncMock(return_value="already_decided"))
    result = await batch.apply_proposals(session, apply=True)
    assert result["accepted"] == 0
    assert result["already_decided"] == 1


def test_application_task_is_registered_on_sync_queue():
    from api.worker.app import app

    task = app.tasks["apps.sync.tasks.season.apply_match_proposals_task"]
    assert task.queue == "sync"
    assert task.time_limit == 3900
