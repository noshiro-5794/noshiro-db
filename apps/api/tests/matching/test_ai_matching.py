from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from api.contexts.matching import service
from api.contexts.matching.domain import MatchProposal, bind_allowed, structured_sides
from api.shared.ai import AIError


@pytest.mark.parametrize("confidence", [True, False, "NaN", "Infinity", -0.1, 1.1, None])
def test_invalid_confidence_is_rejected(confidence):
    with pytest.raises(ValidationError):
        MatchProposal.model_validate(
            {"decision": "bind", "confidence": confidence, "reason": "same"}
        )


@pytest.mark.parametrize("decision,reason", [("merge", "same"), ("bind", "  "), ("bind", 123)])
def test_invalid_decision_or_reason_is_rejected(decision, reason):
    with pytest.raises(ValidationError):
        MatchProposal(decision=decision, confidence=1, reason=reason)


def test_evidence_is_oriented_using_provider_entity_ids():
    result = structured_sides(
        "left",
        [
            {
                "evidence_type": "work_attributes",
                "value": {
                    "source_entity_id": "right",
                    "target_entity_id": "left",
                    "source": {"names": ["Source"]},
                    "target": {"names": ["Target"]},
                    "comparison": {"release_year_delta": 0},
                },
            }
        ],
    )
    assert result["left"] == {"names": ["Target"]}
    assert result["right"] == {"names": ["Source"]}


def binding_inputs():
    return dict(
        proposal=MatchProposal(decision="bind", confidence="0.9999", reason="same work"),
        candidate=SimpleNamespace(
            score=Decimal("0.9999"), runner_up_margin=Decimal("0.1"), hard_conflicts=[]
        ),
        policy=SimpleNamespace(
            minimum_score=Decimal("0.995"), minimum_margin=Decimal("0.05"), minimum_evidence_types=2
        ),
        evidence_types=2,
        left_kind="work",
        right_kind="work",
        left_types={"anime"},
        right_types={"anime"},
        library_conflict=False,
    )


def test_binding_requires_every_independent_gate():
    assert bind_allowed(**binding_inputs())
    for key, value in (
        ("evidence_types", 1),
        ("left_types", set()),
        ("right_types", {"galgame"}),
        ("library_conflict", True),
        ("right_kind", "character"),
    ):
        inputs = binding_inputs()
        inputs[key] = value
        assert not bind_allowed(**inputs)
    inputs = binding_inputs()
    inputs["candidate"].hard_conflicts = [{"type": "release_year_conflict"}]
    assert not bind_allowed(**inputs)


@pytest.mark.asyncio
async def test_shadow_policy_preserves_candidate_and_pending_proposal(monkeypatch):
    query = AsyncMock()
    decide = AsyncMock()
    monkeypatch.setattr(service, "fetch", query)
    monkeypatch.setattr(service.resolution, "decide", decide)
    await service.apply_policy(
        object(),
        SimpleNamespace(status="pending"),
        SimpleNamespace(is_enabled=True, shadow_mode=True),
        MatchProposal(decision="bind", confidence=1, reason="same"),
        "proposal",
        2,
    )
    decide.assert_not_awaited()
    assert "Shadow proposal only" in query.await_args.args[2]["reason"]


@pytest.mark.asyncio
async def test_failed_model_run_is_recorded_after_candidate_transaction_rolls_back(monkeypatch):
    events = []

    @asynccontextmanager
    async def scope():
        try:
            yield object()
        except Exception:
            events.append("rollback")
            raise

    candidate = SimpleNamespace(
        id=UUID(int=1),
        left_entity_id=UUID(int=2),
        right_entity_id=UUID(int=3),
        score=Decimal("0.9"),
        runner_up_margin=Decimal("0.1"),
        hard_conflicts=[],
        policy_version="title-similarity-v2",
    )
    monkeypatch.setattr(service, "session_scope", scope)
    monkeypatch.setattr(service, "fetch", AsyncMock(side_effect=[[candidate], []]))
    monkeypatch.setattr(service, "policy_for", AsyncMock(return_value=object()))
    monkeypatch.setattr(service, "start_run", AsyncMock(return_value=UUID(int=4)))
    monkeypatch.setattr(
        service, "complete_json", AsyncMock(side_effect=AIError("unpaid", status_code=402))
    )

    async def failed(run_id, error):
        assert events == ["rollback"]
        assert run_id == UUID(int=4)
        assert error.status_code == 402
        events.append("failure recorded")

    monkeypatch.setattr(service, "fail_run", failed)
    with pytest.raises(AIError):
        await service.evaluate(str(candidate.id))
    assert events == ["rollback", "failure recorded"]


@pytest.mark.asyncio
async def test_pending_recovery_dispatches_only_successfully_published_ids(monkeypatch):
    from api.worker.tasks import ai as ai_tasks

    @asynccontextmanager
    async def scope():
        yield object()

    monkeypatch.setattr(ai_tasks, "session_scope", scope)
    monkeypatch.setattr(ai_tasks.settings, "ai_base_url", "https://provider.test")
    monkeypatch.setattr(ai_tasks.settings, "ai_api_key", "key")
    monkeypatch.setattr(ai_tasks, "provider_available", AsyncMock(return_value=True))
    query = AsyncMock(
        return_value=[SimpleNamespace(id=UUID(int=1)), SimpleNamespace(id=UUID(int=2))]
    )
    monkeypatch.setattr(ai_tasks, "fetch", query)
    calls = []

    def publish(task, kwargs, *, queue):
        calls.append((task, kwargs, queue))
        return "sent" if kwargs["candidate_id"] == str(UUID(int=1)) else None

    monkeypatch.setattr(ai_tasks, "publish", publish)
    result = await ai_tasks.dispatch_pending(10)
    assert result == {"dispatched": 1, "candidate_ids": [str(UUID(int=1))]}
    assert len(calls) == 2
    assert query.await_args.args[2]["limit"] == 10
    assert "NOT EXISTS" in query.await_args.args[1]


@pytest.mark.asyncio
async def test_pending_recovery_respects_provider_cooldown(monkeypatch):
    from api.worker.tasks import ai as ai_tasks

    monkeypatch.setattr(ai_tasks.settings, "ai_base_url", "https://provider.test")
    monkeypatch.setattr(ai_tasks.settings, "ai_api_key", "key")
    monkeypatch.setattr(ai_tasks, "provider_available", AsyncMock(return_value=False))
    query = AsyncMock()
    monkeypatch.setattr(ai_tasks, "fetch", query)
    assert await ai_tasks.dispatch_pending(10) == {
        "dispatched": 0,
        "reason": "ai_provider_unavailable",
    }
    query.assert_not_awaited()


@pytest.mark.asyncio
async def test_success_persists_validated_output_usage_and_applies_policy(monkeypatch):
    @asynccontextmanager
    async def scope():
        yield object()

    candidate = SimpleNamespace(
        id=UUID(int=1),
        left_entity_id=UUID(int=2),
        right_entity_id=UUID(int=3),
        score=Decimal("0.9"),
        runner_up_margin=Decimal("0.1"),
        hard_conflicts=[],
        policy_version="title-similarity-v2",
    )
    query = AsyncMock(side_effect=[[candidate], [], [], [SimpleNamespace(id=UUID(int=5))]])
    monkeypatch.setattr(service, "session_scope", scope)
    monkeypatch.setattr(service, "fetch", query)
    monkeypatch.setattr(service, "policy_for", AsyncMock(return_value=object()))
    monkeypatch.setattr(service, "start_run", AsyncMock(return_value=UUID(int=4)))
    monkeypatch.setattr(
        service,
        "complete_json",
        AsyncMock(
            return_value=(
                {"decision": "abstain", "confidence": "0.5", "reason": " insufficient evidence "},
                {"prompt_tokens": 10, "completion_tokens": 5},
            )
        ),
    )
    apply = AsyncMock()
    failed = AsyncMock()
    monkeypatch.setattr(service, "apply_policy", apply)
    monkeypatch.setattr(service, "fail_run", failed)
    assert await service.evaluate(str(candidate.id)) == str(UUID(int=5))
    run_update = query.await_args_list[2].args[2]
    assert run_update["input"] == 10
    assert run_update["output_tokens"] == 5
    apply.assert_awaited_once()
    assert apply.await_args.args[3].reason == "insufficient evidence"
    failed.assert_not_awaited()
