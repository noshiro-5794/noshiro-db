import json
from time import monotonic
from unittest.mock import AsyncMock

import pytest

from api.contexts.index import resolution
from api.contexts.knowledge import enrichment, normalization, web_evidence
from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization import campaign_ai, campaigns, work_items
from api.contexts.synchronization.domain import LeaseLost
from api.worker.subject_import import import_subject
from tests.test_normalization_transactions import normalization_runtime as normalization_runtime

NORMALIZED = {
    "action": "preserve_raw",
    "preferred_term": "SF",
    "confidence": 0.8,
    "reason": "Preserve provider vocabulary",
}
ENRICHED = {
    "strategy": "complete",
    "proposals": [
        {
            "field": "title",
            "language": "zh",
            "script": "Hans",
            "text": "标题",
            "kind": "translated",
            "confidence": 0.99,
            "reason": "Supported",
            "source": "model",
        }
    ],
}


@pytest.fixture
async def campaign_runtime(normalization_runtime, monkeypatch):
    session, context, model = normalization_runtime
    await import_subject(session, {"id": 1, "type": 2, "name": "Anime", "genres": ["SF", "Drama"]})
    identifier = await campaigns.create_campaign(session, provider="bangumi", ai_mode="shadow")
    await campaigns.transition(session, identifier, "queued", "discovering")
    await work_items.enqueue_page(session, identifier, 1, ["1"])
    await campaigns.transition(session, identifier, "discovering", "fetching")
    item = (await work_items.claim_items(session, identifier, "importer"))[0]
    await work_items.succeed(session, item.id, "importer", {"entity_id": str(context.entity_id)})
    await campaigns.transition(session, identifier, "fetching", "mapping")
    await campaigns.transition(session, identifier, "mapping", "normalizing")
    await campaigns.claim_campaign(session, identifier, "worker")
    await session.commit()
    monkeypatch.setattr(campaign_ai, "session_scope", normalization.session_scope)
    monkeypatch.setattr(enrichment, "session_scope", normalization.session_scope)
    monkeypatch.setattr(web_evidence, "gather", AsyncMock(return_value=[]))
    completion = AsyncMock(return_value=(ENRICHED, {}))
    monkeypatch.setattr(enrichment, "complete_json", completion)
    model.return_value = (NORMALIZED, {})
    return session, identifier, item.id, model, completion


@pytest.mark.asyncio
async def test_normalizing_phase_completes_fields_once_and_reuses_one_campaign_run(
    campaign_runtime,
):
    session, identifier, item_id, model, _ = campaign_runtime
    assert await campaign_ai.run_phase(
        identifier, "worker", "normalizing", deadline=monotonic() + 60
    )
    assert model.await_count == 2
    campaign = await campaigns.get_campaign(session, identifier)
    assert campaign.agent_run_id is not None
    assert (
        await fetch(
            session, "SELECT ai_processed_at FROM sync_work_item WHERE id=:id", {"id": item_id}
        )
    )[0].ai_processed_at is not None
    assert await campaign_ai.run_phase(
        identifier, "worker", "normalizing", deadline=monotonic() + 60
    )
    assert model.await_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 2
    run = (
        await fetch(
            session, "SELECT metadata FROM agent_run WHERE id=:id", {"id": campaign.agent_run_id}
        )
    )[0]
    assert run.metadata["campaign_id"] == str(identifier)


@pytest.mark.asyncio
async def test_normalization_resumes_field_checkpoint_without_repeating_paid_calls(
    campaign_runtime,
    monkeypatch,
):
    session, identifier, _, model, _ = campaign_runtime
    clock = [0.0]
    monkeypatch.setattr(campaign_ai, "monotonic", lambda: clock[0])

    async def complete_one(**kwargs):
        clock[0] = 2.0
        return NORMALIZED, {}

    model.side_effect = complete_one
    assert not await campaign_ai.run_phase(identifier, "worker", "normalizing", deadline=1.0)
    assert model.await_count == 1
    clock[0] = 0.0
    model.side_effect = None
    model.return_value = (NORMALIZED, {})
    assert await campaign_ai.run_phase(identifier, "worker", "normalizing", deadline=1.0)
    assert model.await_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 2


@pytest.mark.asyncio
async def test_required_mode_retains_raw_audit_then_retries_when_model_recovers(campaign_runtime):
    session, identifier, _, model, _ = campaign_runtime
    await fetch(
        session,
        "UPDATE sync_campaign SET ai_mode='required' WHERE id=:id RETURNING id",
        {"id": identifier},
    )
    await session.commit()
    model.return_value = ({"action": "invalid"}, {})
    with pytest.raises(campaign_ai.AIRequiredError):
        await campaign_ai.run_phase(identifier, "worker", "normalizing", deadline=monotonic() + 60)
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 1
    model.return_value = (NORMALIZED, {})
    assert await campaign_ai.run_phase(
        identifier, "worker", "normalizing", deadline=monotonic() + 60
    )
    assert model.await_count == 3


@pytest.mark.asyncio
async def test_cancelled_campaign_cannot_persist_post_model_claims(campaign_runtime):
    session, identifier, _, model, _ = campaign_runtime

    async def cancel(**kwargs):
        await campaigns.control(session, str(identifier), "cancel")
        await session.commit()
        return NORMALIZED, {}

    model.side_effect = cancel
    with pytest.raises(LeaseLost):
        await campaign_ai.run_phase(identifier, "worker", "normalizing", deadline=monotonic() + 60)
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 0
    assert (await campaigns.get_campaign(session, identifier)).status == "cancelled"


@pytest.mark.asyncio
async def test_enrichment_phase_updates_item_and_campaign_counts_atomically(campaign_runtime):
    session, identifier, item_id, _, completion = campaign_runtime
    await campaigns.transition(session, identifier, "normalizing", "reconciling")
    await campaigns.transition(session, identifier, "reconciling", "enriching")
    await fetch(
        session,
        "UPDATE sync_campaign SET parameters=CAST(:params AS jsonb) WHERE id=:id RETURNING id",
        {
            "id": identifier,
            "params": json.dumps(
                {
                    "enrich_apply": True,
                    "enrich_languages": ["zh"],
                }
            ),
        },
    )
    await session.commit()
    assert await campaign_ai.run_phase(identifier, "worker", "enriching", deadline=monotonic() + 60)
    completion.assert_awaited_once()
    row = await campaigns.get_campaign(session, identifier)
    assert row.parameters["enrichment"] == {"claims": 1, "applied": 1, "abstained": 0, "skipped": 0}
    assert (
        await fetch(
            session, "SELECT ai_enriched_at FROM sync_work_item WHERE id=:id", {"id": item_id}
        )
    )[0].ai_enriched_at is not None


@pytest.mark.asyncio
async def test_off_mode_does_not_allocate_agent_or_call_models(campaign_runtime):
    session, identifier, _, model, completion = campaign_runtime
    await fetch(
        session,
        "UPDATE sync_campaign SET ai_mode='off' WHERE id=:id RETURNING id",
        {"id": identifier},
    )
    await session.commit()
    assert await campaign_ai.run_phase(
        identifier, "worker", "normalizing", deadline=monotonic() + 60
    )
    assert (await campaigns.get_campaign(session, identifier)).agent_run_id is None
    model.assert_not_awaited()
    completion.assert_not_awaited()


@pytest.mark.asyncio
async def test_canonical_target_accepts_evidence_from_merged_source(campaign_runtime):
    session, identifier, item_id, model, _ = campaign_runtime
    original = (
        await fetch(session, "SELECT result FROM sync_work_item WHERE id=:id", {"id": item_id})
    )[0].result["entity_id"]
    root = await import_subject(session, {"id": 2, "type": 2, "name": "Canonical"})
    await resolution.merge(
        session, source_id=original, target_id=root, method="manual", reason="Fixture"
    )
    await fetch(
        session,
        "UPDATE sync_work_item SET result=CAST(:result AS jsonb) WHERE id=:id RETURNING id",
        {"id": item_id, "result": json.dumps({"entity_id": str(root)})},
    )
    await session.commit()
    assert await campaign_ai.run_phase(
        identifier, "worker", "normalizing", deadline=monotonic() + 60
    )
    assert model.await_count == 2
    rows = await fetch(session, "SELECT target_entity_id FROM ai_claim", {})
    assert all(row.target_entity_id == root for row in rows)
