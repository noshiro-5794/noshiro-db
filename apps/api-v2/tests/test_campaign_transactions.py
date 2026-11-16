from uuid import uuid4

import httpx
import pytest

from api.contexts.access.dependencies import staff_user
from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization import campaigns, work_items
from api.contexts.synchronization.domain import LeaseLost
from api.db import get_session
from api.main import create_app
from api.worker.providers.errors import ProviderError


async def discovering(session):
    identifier = await campaigns.create_campaign(session, provider="bangumi", ai_mode="off")
    assert await campaigns.transition(session, identifier, "queued", "discovering")
    return identifier


@pytest.mark.asyncio
async def test_idempotent_campaign_creation_uses_partial_unique_key(integration_session):
    session = integration_session
    key = str(uuid4())
    first = await campaigns.create_campaign(session, provider="bangumi", idempotency_key=key)
    second = await campaigns.create_campaign(session, provider="bangumi", idempotency_key=key)
    assert first == second
    assert first != await campaigns.create_campaign(session, provider="bangumi")


@pytest.mark.asyncio
async def test_campaign_lease_rejects_another_owner_and_releases_conditionally(integration_session):
    session = integration_session
    identifier = await discovering(session)
    assert await campaigns.claim_campaign(session, identifier, "first")
    assert await campaigns.claim_campaign(session, identifier, "second") is None
    assert not await campaigns.release(session, identifier, "second")
    assert await campaigns.heartbeat(session, identifier, "first")
    assert await campaigns.release(session, identifier, "first")
    assert await campaigns.claim_campaign(session, identifier, "second")


@pytest.mark.asyncio
async def test_page_replay_and_stale_owner_cannot_duplicate_completion(integration_session):
    session = integration_session
    identifier = await discovering(session)
    assert await work_items.enqueue_page(session, identifier, 1, ["1", "2"]) == 2
    assert await work_items.enqueue_page(session, identifier, 1, ["1", "2"]) == 0
    assert await campaigns.transition(session, identifier, "discovering", "fetching")
    first = await work_items.claim_items(session, identifier, "first", limit=1)
    item = first[0]
    with pytest.raises(LeaseLost):
        await work_items.succeed(session, item.id, "wrong", {})
    await fetch(
        session,
        "UPDATE sync_work_item SET lease_expires_at=now()-interval '1 second' "
        "WHERE id=:id RETURNING id",
        {"id": item.id},
    )
    reclaimed = await work_items.claim_items(session, identifier, "second", limit=2)
    assert any(row.id == item.id and row.attempt == 2 for row in reclaimed)
    with pytest.raises(LeaseLost):
        await work_items.succeed(session, item.id, "first", {})
    await work_items.succeed(session, item.id, "second", {"entity_id": str(uuid4())})
    with pytest.raises(LeaseLost):
        await work_items.succeed(session, item.id, "second", {})
    campaign = await campaigns.get_campaign(session, identifier)
    assert campaign.processed_items == campaign.synced_items == 1


@pytest.mark.asyncio
async def test_retry_and_terminal_failure_counts_survive_resume(integration_session):
    session = integration_session
    identifier = await discovering(session)
    await work_items.enqueue_page(session, identifier, 1, ["1"])
    await campaigns.transition(session, identifier, "discovering", "fetching")
    item = (await work_items.claim_items(session, identifier, "worker"))[0]
    status = await work_items.fail(
        session, item.id, "worker", ProviderError("rate limit", status_code=429)
    )
    assert status == "queued"
    assert (await campaigns.get_campaign(session, identifier)).processed_items == 0
    await fetch(
        session,
        "UPDATE sync_work_item SET next_retry_at=now() WHERE id=:id RETURNING id",
        {"id": item.id},
    )
    await work_items.claim_items(session, identifier, "worker")
    status = await work_items.fail(
        session, item.id, "worker", ProviderError("invalid", status_code=400)
    )
    assert status == "failed"
    await campaigns.transition(session, identifier, "fetching", "failed")
    await campaigns.resume_failed(session, identifier)
    campaign = await campaigns.get_campaign(session, identifier)
    assert campaign.processed_items == campaign.failed_items == 0


@pytest.mark.asyncio
async def test_cancellation_invalidates_running_item_leases(integration_session):
    session = integration_session
    identifier = await discovering(session)
    await work_items.enqueue_page(session, identifier, 1, ["1"])
    await campaigns.transition(session, identifier, "discovering", "fetching")
    item = (await work_items.claim_items(session, identifier, "worker"))[0]
    await campaigns.control(session, str(identifier), "cancel")
    with pytest.raises(LeaseLost):
        await work_items.succeed(session, item.id, "worker", {})
    assert await work_items.claim_items(session, identifier, "worker") == []


@pytest.mark.asyncio
async def test_campaign_controls_work_through_staff_http_routes(integration_session, monkeypatch):
    session = integration_session
    identifier = await discovering(session)
    app = create_app()

    async def sessions():
        yield session

    app.dependency_overrides[get_session] = sessions
    app.dependency_overrides[staff_user] = lambda: object()
    calls = []
    monkeypatch.setattr("api.shared.dispatch.publish", lambda task, kwargs: calls.append(kwargs))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        path = f"/api/v1/operations/sync/{identifier}"
        paused = await client.post(f"{path}/pause/")
        assert paused.status_code == 200, paused.text
        assert paused.json()["parameters"]["paused_from"] == "discovering"
        resumed = await client.post(f"{path}/resume/")
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["status"] == "discovering"
        assert calls == [{"campaign_id": str(identifier)}]
        assert (await client.post(f"{path}/cancel/")).json()["status"] == "cancelled"
        assert (await client.post(f"{path}/unknown/")).status_code == 404
        assert (await client.post("/api/v1/operations/sync/invalid/pause/")).status_code == 404


@pytest.mark.asyncio
async def test_campaign_creation_commits_before_dispatch_and_retry_republishes(
    integration_session, monkeypatch
):
    from api.contexts.community import campaigns as api_campaigns

    session = integration_session
    events = []
    commit = session.commit

    async def committed():
        await commit()
        events.append("committed")

    def publish(task, kwargs):
        assert events[-1] == "committed"
        events.append("published")

    monkeypatch.setattr(session, "commit", committed)
    monkeypatch.setattr(api_campaigns, "publish", publish)
    body = {"provider": "bangumi", "ai_mode": "off", "idempotency_key": str(uuid4())}
    first = await api_campaigns.create_campaign(session, body=body)
    second = await api_campaigns.create_campaign(session, body=body)
    assert first["id"] == second["id"]
    assert events == ["committed", "published", "committed", "published"]
