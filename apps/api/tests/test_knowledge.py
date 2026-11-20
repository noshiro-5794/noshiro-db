from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from api.contexts.knowledge import service
from api.contexts.knowledge.domain import Classification, EvidenceClaim, Extraction


def claim(**overrides):
    return {
        "predicate": "episode-count",
        "value": 12,
        "value_type": "number",
        "json_pointer": "/episodes",
        "confidence": "0.9",
        **overrides,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"predicate": "Invalid Name"},
        {"predicate": "-bad"},
        {"value_type": "sql"},
        {"language": "x" * 36},
        {"spoiler_level": True},
        {"spoiler_level": "1"},
        {"spoiler_level": 4},
        {"safety": "private"},
        {"json_pointer": "episodes"},
        {"confidence": True},
        {"confidence": "NaN"},
        {"confidence": "Infinity"},
        {"confidence": -1},
    ],
)
def test_invalid_evidence_is_rejected(overrides):
    with pytest.raises(ValidationError):
        EvidenceClaim.model_validate(claim(**overrides))


def test_extraction_preserves_claim_fields_and_uses_lowest_confidence():
    output = Extraction.model_validate({"claims": [claim(), claim(confidence="0.6")]})
    assert output.confidence == Decimal("0.6")
    assert output.model_dump(mode="json")["claims"][0] == {
        **claim(),
        "language": "",
        "spoiler_level": 0,
        "safety": "unknown",
    }
    assert Extraction(claims=[]).confidence == 0
    with pytest.raises(ValidationError):
        Extraction.model_validate({"claims": [claim()] * 101})


@pytest.mark.parametrize(
    "field,value",
    [("work_type", "person"), ("confidence", False), ("confidence", 1.1), ("reason", " ")],
)
def test_invalid_classification_is_rejected(field, value):
    with pytest.raises(ValidationError):
        Classification.model_validate(
            {"work_type": "anime", "confidence": "0.99", "reason": "stated", field: value}
        )


@pytest.fixture
def workflow(monkeypatch):
    @asynccontextmanager
    async def scope():
        yield object()

    monkeypatch.setattr(service, "session_scope", scope)
    entity = SimpleNamespace(id=UUID(int=1), kind="work")
    target = AsyncMock(return_value=(entity, {entity.id}, True))
    complete = AsyncMock(return_value="proposal")
    abstain = AsyncMock(return_value="abstained")
    monkeypatch.setattr(service, "target", target)
    monkeypatch.setattr(service, "complete", complete)
    monkeypatch.setattr(service, "abstain", abstain)
    return entity, target, complete, abstain


@pytest.mark.asyncio
async def test_restricted_entity_abstains_before_fetching_projection(monkeypatch, workflow):
    entity, target, complete, abstain = workflow
    target.return_value = entity, {entity.id}, False
    projection = AsyncMock()
    monkeypatch.setattr(service, "entity_detail", projection)
    assert await service.classify_entity(str(entity.id)) == "abstained"
    projection.assert_not_awaited()
    complete.assert_not_awaited()
    assert "Restricted entities" in abstain.await_args.kwargs["output"]["reason"]


@pytest.mark.asyncio
async def test_all_represented_providers_must_allow_classification(monkeypatch, workflow):
    entity, _, complete, abstain = workflow
    monkeypatch.setattr(service, "fetch", AsyncMock(return_value=[SimpleNamespace(slug="blocked")]))
    assert await service.classify_entity(str(entity.id)) == "abstained"
    complete.assert_not_awaited()
    assert "blocked" in abstain.await_args.kwargs["output"]["reason"]


@pytest.mark.asyncio
async def test_classification_uses_safe_public_projection(monkeypatch, workflow):
    entity, _, complete, _ = workflow
    monkeypatch.setattr(service, "fetch", AsyncMock(return_value=[]))
    projection = {"id": str(entity.id), "names": []}
    monkeypatch.setattr(service, "entity_detail", AsyncMock(return_value=projection))
    assert await service.classify_entity(str(entity.id)) == "proposal"
    assert complete.await_args.kwargs["payload"] == projection
    assert complete.await_args.kwargs["prompt_version"] == "entity-classification-v1"


@pytest.mark.asyncio
@pytest.mark.parametrize("active,current", [(False, False), (True, False)])
async def test_extraction_requires_active_current_observation(
    monkeypatch, workflow, active, current
):
    entity, _, complete, abstain = workflow
    observation = SimpleNamespace(id=UUID(int=2), provider_record_id=UUID(int=3))
    replies = [[observation], [object()] if active else []]
    if active:
        replies.append([object()] if current else [])
    monkeypatch.setattr(service, "fetch", AsyncMock(side_effect=replies))
    with pytest.raises(service.InputNotAllowed):
        await service.extract_evidence(str(observation.id), str(entity.id))
    complete.assert_not_awaited()
    abstain.assert_not_awaited()


@pytest.mark.asyncio
async def test_extraction_checks_provider_permission_before_transmitting_payload(
    monkeypatch, workflow
):
    entity, _, complete, abstain = workflow
    observation = SimpleNamespace(
        id=UUID(int=2),
        provider_record_id=UUID(int=3),
        provider_slug="blocked",
        ai_usage_policy="forbidden",
    )
    monkeypatch.setattr(
        service, "fetch", AsyncMock(side_effect=[[observation], [object()], [object()]])
    )
    assert await service.extract_evidence(str(observation.id), str(entity.id)) == "abstained"
    complete.assert_not_awaited()
    assert abstain.await_args.kwargs["observation_id"] == observation.id


@pytest.mark.asyncio
async def test_oversized_payload_is_rejected_before_inference_run(monkeypatch):
    start = AsyncMock()
    monkeypatch.setattr(service, "start_run", start)
    with pytest.raises(service.InputNotAllowed):
        await service.complete(
            use_case="entity_classification",
            prompt_version="v1",
            metadata={},
            system="classify",
            payload={"data": "界" * 40000},
            entity_id=UUID(int=1),
        )
    start.assert_not_awaited()


def test_knowledge_tasks_are_registered_with_bounded_retries():
    from api.worker.app import app

    for name in ("classify_entity_task", "extract_observation_evidence_task"):
        task = app.tasks[f"apps.ai.tasks.{name}"]
        assert task.queue == "ai"
        assert task.max_retries == 3
        assert task.time_limit == 210
