from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from api.contexts.knowledge import service
from api.contexts.knowledge.domain import Classification


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
    monkeypatch.setattr(service, "build_bundle", projection)
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
    monkeypatch.setattr(service, "build_bundle", AsyncMock(return_value={"bundle": projection}))
    assert await service.classify_entity(str(entity.id)) == "proposal"
    assert complete.await_args.kwargs["payload"] == projection
    assert complete.await_args.kwargs["prompt_version"] == "entity-classification-v2"


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

    task = app.tasks["apps.ai.tasks.classify_entity_task"]
    assert task.queue == "ai"
    assert task.max_retries == 3
    assert task.time_limit == 210
