from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from api.contexts.knowledge import enrichment, normalization, web_evidence
from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization import campaign_ai, campaigns, discovery_step
from api.shared import inference
from api.worker import campaign_imports, campaign_tasks
from api.worker.bangumi_sync import SubjectBatch
from api.worker.providers.catalog import CatalogPage
from api.worker.providers.errors import ProviderError


def batch(identifier):
    return SubjectBatch(
        {"id": int(identifier), "type": 2, "name": f"Anime {identifier}"},
        [],
        [],
        [],
        [],
        {},
        {},
    )


@pytest.fixture
async def runtime(bangumi_session, monkeypatch):
    session = bangumi_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    for module in [campaign_tasks, campaign_ai, enrichment, normalization, inference]:
        monkeypatch.setattr(module, "session_scope", scope)
    discovery = AsyncMock(return_value=CatalogPage(("1",), None))
    monkeypatch.setattr(discovery_step, "discover_page", discovery)

    async def fetched(provider, identifier, **kwargs):
        return batch(identifier)

    importer = AsyncMock(side_effect=fetched)
    monkeypatch.setattr(campaign_imports, "fetch_source", importer)
    monkeypatch.setattr(web_evidence, "gather", AsyncMock(return_value=[]))
    identifier = await campaigns.create_campaign(session, provider="bangumi", ai_mode="off")
    await session.commit()
    return session, identifier, discovery, importer


@pytest.mark.asyncio
async def test_campaign_executes_all_phases_and_completed_replay_is_a_noop(runtime):
    session, identifier, _, importer = runtime
    outcome = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert outcome.result == {
        "campaign_id": str(identifier),
        "provider": "bangumi",
        "status": "completed",
        "processed_items": 1,
        "failed_items": 0,
    }
    assert outcome.countdown is None
    campaign = await campaigns.get_campaign(session, identifier)
    assert campaign.lease_owner == ""
    assert campaign.next_run_at is None
    assert campaign.quality_report["succeeded_items"] == 1
    assert campaign.quality_report["evidence_first"] is True
    assert campaign.agent_run_id is None
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 1
    again = await campaign_tasks.execute(str(identifier), max_items=None, owner="replay")
    assert again == outcome
    importer.assert_awaited_once()


@pytest.mark.asyncio
async def test_discovery_persists_cursor_then_reschedules_remaining_page(runtime):
    session, identifier, discovery, importer = runtime
    discovery.side_effect = [CatalogPage(("1",), "2"), CatalogPage(("2",), None)]
    first = await campaign_tasks.execute(str(identifier), max_items=None, owner="first")
    assert first.result["status"] == "discovering"
    assert first.countdown == 1
    importer.assert_not_awaited()
    row = await campaigns.get_campaign(session, identifier)
    assert row.parameters["discovery"]["next_cursor"] == "2"
    second = await campaign_tasks.execute(str(identifier), max_items=None, owner="second")
    assert second.result["status"] == "completed"
    assert second.result["processed_items"] == 2
    assert importer.await_count == 2


@pytest.mark.asyncio
async def test_fetch_batch_limit_resumes_remaining_items_without_reimport(runtime):
    _, identifier, discovery, importer = runtime
    discovery.return_value = CatalogPage(("1", "2"), None)
    first = await campaign_tasks.execute(str(identifier), max_items=1, owner="first")
    assert first.result["status"] == "fetching"
    assert first.result["processed_items"] == 1
    second = await campaign_tasks.execute(str(identifier), max_items=1, owner="second")
    assert second.result["status"] == "completed"
    assert second.result["processed_items"] == 2
    assert importer.await_count == 2


@pytest.mark.asyncio
async def test_retryable_source_failure_uses_persisted_retry_time(runtime):
    session, identifier, _, importer = runtime
    importer.side_effect = [
        ProviderError("temporarily unavailable", status_code=503, retry_after=2),
        batch("1"),
    ]
    first = await campaign_tasks.execute(str(identifier), max_items=None, owner="first")
    assert first.result["status"] == "fetching"
    assert first.countdown >= 2
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0
    await fetch(
        session,
        "UPDATE sync_work_item SET next_retry_at=now()-interval '1 second' RETURNING id",
        {},
    )
    await session.commit()
    second = await campaign_tasks.execute(str(identifier), max_items=None, owner="second")
    assert second.result["status"] == "completed"
    assert (await fetch(session, "SELECT attempt FROM sync_work_item", {}))[0].attempt == 2


@pytest.mark.asyncio
async def test_exhausted_failure_can_be_explicitly_resumed(runtime):
    _, identifier, _, importer = runtime
    importer.side_effect = [ValueError("invalid payload"), batch("1")]
    first = await campaign_tasks.execute(str(identifier), max_items=None, owner="first")
    assert first.result["status"] == "failed"
    assert first.countdown is None
    assert first.result["failed_items"] == 1
    second = await campaign_tasks.execute(str(identifier), max_items=None, owner="second")
    assert second.result["status"] == "completed"
    assert second.result["failed_items"] == 0
    assert second.result["processed_items"] == 1


@pytest.mark.asyncio
async def test_cancel_during_fetch_prevents_catalogue_projection(runtime):
    session, identifier, _, importer = runtime

    async def cancelled(*args, **kwargs):
        await campaigns.control(session, str(identifier), "cancel")
        await session.commit()
        return batch("1")

    importer.side_effect = cancelled
    outcome = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert outcome.result["status"] == "cancelled"
    assert outcome.countdown is None
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0


@pytest.mark.asyncio
async def test_pause_finishes_inflight_item_and_resume_advances_without_refetch(runtime):
    session, identifier, _, importer = runtime

    async def paused(*args, **kwargs):
        await campaigns.control(session, str(identifier), "pause")
        await session.commit()
        return batch("1")

    importer.side_effect = paused
    first = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert first.result["status"] == "paused"
    assert first.result["processed_items"] == 1
    assert first.countdown is None
    await campaigns.control(session, str(identifier), "resume")
    await session.commit()
    second = await campaign_tasks.execute(str(identifier), max_items=None, owner="second")
    assert second.result["status"] == "completed"
    importer.assert_awaited_once()


@pytest.mark.asyncio
async def test_changed_lease_owner_cannot_project_or_change_new_owners_schedule(runtime):
    session, identifier, _, importer = runtime

    async def changed(*args, **kwargs):
        await fetch(
            session,
            "UPDATE sync_campaign SET lease_owner='other',"
            "lease_expires_at=clock_timestamp()+interval '10 minutes' WHERE id=:id RETURNING id",
            {"id": identifier},
        )
        await session.commit()
        return batch("1")

    importer.side_effect = changed
    outcome = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert outcome.result["status"] == "fetching"
    assert outcome.countdown >= 599
    row = await campaigns.get_campaign(session, identifier)
    assert row.lease_owner == "other"
    assert row.next_run_at is None
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0


@pytest.mark.asyncio
async def test_projection_and_work_acknowledgement_roll_back_together(runtime, monkeypatch):
    session, identifier, _, _ = runtime
    original = campaign_imports.project_source

    async def fail_after_project(*args, **kwargs):
        await original(*args, **kwargs)
        raise ValueError("projection failed")

    monkeypatch.setattr(campaign_imports, "project_source", fail_after_project)
    outcome = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert outcome.result["status"] == "failed"
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0
    assert (await fetch(session, "SELECT status FROM sync_work_item", {}))[0].status == "failed"


@pytest.mark.asyncio
async def test_shadow_and_assisted_ai_phases_finish_one_durable_run(runtime, monkeypatch):
    session, identifier, _, importer = runtime
    await fetch(
        session,
        "UPDATE sync_campaign SET ai_mode='assisted',"
        "parameters='{}'::jsonb||CAST(:params AS jsonb) WHERE id=:id RETURNING id",
        {"id": identifier, "params": '{"enrich_apply":true,"enrich_languages":["zh"]}'},
    )
    await session.commit()

    async def tagged(*args, **kwargs):
        result = batch("1")
        result.subject["genres"] = ["SF"]
        return result

    importer.side_effect = tagged
    monkeypatch.setattr(
        normalization,
        "complete_json",
        AsyncMock(
            return_value=(
                {
                    "action": "preserve_raw",
                    "preferred_term": "SF",
                    "confidence": 0.8,
                    "reason": "Provider genre",
                },
                {},
            )
        ),
    )
    monkeypatch.setattr(
        enrichment,
        "complete_json",
        AsyncMock(
            return_value=(
                {
                    "strategy": "complete",
                    "proposals": [
                        {
                            "field": "title",
                            "language": "zh",
                            "script": "Hans",
                            "text": "标题",
                            "confidence": 0.99,
                            "source": "model",
                        }
                    ],
                },
                {},
            )
        ),
    )
    outcome = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert outcome.result["status"] == "completed"
    row = await campaigns.get_campaign(session, identifier)
    assert row.parameters["enrichment"]["applied"] == 1
    assert row.quality_report["ai_claims_pending_review"] == 1
    assert (
        await fetch(session, "SELECT status FROM agent_run WHERE id=:id", {"id": row.agent_run_id})
    )[0].status == "succeeded"
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_run", {}))[0].n == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_name WHERE text='标题'", {}))[
        0
    ].n == 1


@pytest.mark.asyncio
async def test_missing_source_id_is_skipped_without_failing_campaign(runtime):
    session, identifier, discovery, importer = runtime
    discovery.return_value = CatalogPage(("1", "2"), None)

    async def found(provider, external_id, **kwargs):
        if external_id == "2":
            raise ProviderError("not found", status_code=404)
        return batch("1")

    importer.side_effect = found
    outcome = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert outcome.result["status"] == "completed"
    row = await campaigns.get_campaign(session, identifier)
    assert (row.processed_items, row.synced_items, row.skipped_items) == (2, 1, 1)
    assert row.quality_report["skipped_items"] == 1


@pytest.mark.asyncio
async def test_incremental_completion_promotes_fallback_watermark(runtime):
    session, identifier, _, _ = runtime
    await fetch(
        session,
        "UPDATE sync_campaign SET campaign_type='incremental' WHERE id=:id RETURNING id",
        {"id": identifier},
    )
    await session.commit()
    outcome = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert outcome.result["status"] == "completed"
    params = (await campaigns.get_campaign(session, identifier)).parameters
    assert params["watermark"].isdigit()
    assert "pending_watermark" not in params


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,external,payload",
    [
        ("bangumi", "1", batch("1")),
        ("vndb", "v1", None),
        ("mal", "1", {"id": 1, "title": "Anime"}),
        ("anilist", "1", {"id": 1, "type": "ANIME", "title": {"romaji": "Anime"}}),
    ],
)
async def test_provider_projection_delegation_uses_complete_importers(
    integration_session,
    register_provider,
    provider,
    external,
    payload,
):
    from api.worker.providers.vndb import VNDBImportBatch

    await register_provider(provider, provider)
    if provider == "vndb":
        payload = VNDBImportBatch(work={"id": "v1", "title": "Visual novel"})
    identifier = await campaign_imports.project_source(
        integration_session, provider, external, payload
    )
    assert identifier is not None
    row = (await fetch(integration_session, "SELECT count(*) AS n FROM work", {}))[0]
    assert row.n == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,truncated,expected",
    [
        ("anilist", False, "missing"),
        ("anilist", True, "active"),
        ("bangumi", False, "active"),
    ],
)
async def test_missing_reconciliation_requires_complete_catalogue_and_preserves_fresh_reads(
    runtime,
    register_provider,
    provider,
    truncated,
    expected,
):
    from api.worker import records

    session, identifier, discovery, importer = runtime
    await register_provider(provider, provider)
    namespace = "subject" if provider == "bangumi" else "anime"
    recorded = await records.record_payload(
        session,
        provider_slug=provider,
        namespace_slug=namespace,
        resource_type=namespace,
        external_id="2",
        payload={"id": 2},
    )
    await fetch(
        session,
        "UPDATE provider_record SET last_seen_at=clock_timestamp()-interval '1 day' "
        "WHERE id=:id RETURNING id",
        {"id": recorded.record_id},
    )
    await fetch(
        session,
        "UPDATE sync_campaign SET provider_slug=:provider,"
        "parameters=CAST(:params AS jsonb) WHERE id=:id RETURNING id",
        {
            "id": identifier,
            "provider": provider,
            "params": '{"max_pages":1}' if truncated else "{}",
        },
    )
    await session.commit()
    discovery.return_value = CatalogPage(("1",), "2" if truncated else None)

    async def fetched(*args, **kwargs):
        await records.record_payload(
            session,
            provider_slug=provider,
            namespace_slug=namespace,
            resource_type=namespace,
            external_id="3",
            payload={"id": 3},
        )
        await session.commit()
        if provider == "bangumi":
            return batch("1")
        return {"id": 1, "type": "ANIME", "title": {"romaji": "Anime"}}

    importer.side_effect = fetched
    outcome = await campaign_tasks.execute(str(identifier), max_items=None, owner="worker")
    assert outcome.result["status"] == "completed"
    rows = await fetch(
        session,
        "SELECT external_id,status FROM provider_record "
        "WHERE namespace_id=(SELECT namespace_id FROM provider_record WHERE id=:id)",
        {"id": recorded.record_id},
    )
    statuses = {row.external_id: row.status for row in rows}
    assert statuses["2"] == expected
    assert statuses["3"] == "active"
