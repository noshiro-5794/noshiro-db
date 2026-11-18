from unittest.mock import AsyncMock

import pytest

from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization import campaigns, discovery_step
from api.contexts.synchronization.domain import LeaseLost
from api.worker.providers.catalog import CatalogPage, DeltaPage


async def campaign(session, **kwargs):
    identifier = await campaigns.create_campaign(
        session, provider="anilist", ai_mode="off", **kwargs
    )
    await campaigns.transition(session, identifier, "queued", "discovering")
    await campaigns.claim_campaign(session, identifier, "worker")
    return identifier


@pytest.mark.asyncio
async def test_discovery_checkpoint_survives_replay_without_duplicate_work(
    integration_session, monkeypatch
):
    session = integration_session
    identifier = await campaign(session)
    page = AsyncMock(return_value=CatalogPage(("1", "2"), None))
    monkeypatch.setattr(discovery_step, "discover_page", page)
    assert await discovery_step.discover_step(session, identifier, "worker")
    assert await discovery_step.discover_step(session, identifier, "worker")
    page.assert_awaited_once()
    rows = await fetch(
        session,
        "SELECT count(*) AS total FROM sync_work_item WHERE campaign_id=:id",
        {"id": identifier},
    )
    assert rows[0].total == 2
    record = await campaigns.get_campaign(session, identifier)
    assert record.parameters["discovery"] == {"pages": 1, "next_cursor": None}
    assert record.total_items == 2


@pytest.mark.asyncio
async def test_pause_during_provider_request_prevents_checkpoint_write(
    integration_session, monkeypatch
):
    session = integration_session
    identifier = await campaign(session)

    async def paused(*args, **kwargs):
        await campaigns.control(session, str(identifier), "pause")
        return CatalogPage(("1",), None)

    monkeypatch.setattr(discovery_step, "discover_page", paused)
    with pytest.raises(LeaseLost):
        await discovery_step.discover_step(session, identifier, "worker")
    rows = await fetch(
        session,
        "SELECT count(*) AS total FROM sync_work_item WHERE campaign_id=:id",
        {"id": identifier},
    )
    assert rows[0].total == 0


@pytest.mark.asyncio
async def test_truncated_delta_does_not_promote_pending_watermark(integration_session, monkeypatch):
    session = integration_session
    identifier = await campaign(session, campaign_type="incremental", parameters={"max_pages": 1})
    monkeypatch.setattr(
        discovery_step, "discover_page", AsyncMock(return_value=DeltaPage(("1",), "2", "20260101"))
    )
    assert await discovery_step.discover_step(session, identifier, "worker")
    record = await campaigns.get_campaign(session, identifier)
    assert record.parameters["discovery"]["truncated"]
    assert "pending_watermark" not in record.parameters


@pytest.mark.asyncio
async def test_delta_window_promotes_anchor_and_restarts_paging(integration_session, monkeypatch):
    session = integration_session
    identifier = await campaign(
        session,
        campaign_type="incremental",
        parameters={
            "watermark": "19400101",
            "discovery_pages_per_step": 2,
            "delta_window_pages": 2,
        },
    )
    pages = AsyncMock(
        side_effect=[DeltaPage(("1",), "2", "20260101"), DeltaPage(("2",), "3", "20260201")]
    )
    monkeypatch.setattr(discovery_step, "discover_page", pages)
    assert not await discovery_step.discover_step(session, identifier, "worker")
    record = await campaigns.get_campaign(session, identifier)
    assert record.parameters["watermark"] == "20260201"
    assert record.parameters["discovery"]["next_cursor"] == "1"
    assert "pending_watermark" not in record.parameters


@pytest.mark.asyncio
async def test_parameter_change_during_fetch_is_not_overwritten(integration_session, monkeypatch):
    session = integration_session
    identifier = await campaign(session)

    async def changed(*args, **kwargs):
        await fetch(
            session,
            "UPDATE sync_campaign SET parameters=CAST(:params AS jsonb) WHERE id=:id RETURNING id",
            {"id": identifier, "params": '{"page_size": 10}'},
        )
        return CatalogPage(("1",), None)

    monkeypatch.setattr(discovery_step, "discover_page", changed)
    with pytest.raises(LeaseLost):
        await discovery_step.discover_step(session, identifier, "worker")
    record = await campaigns.get_campaign(session, identifier)
    assert record.parameters == {"page_size": 10}
