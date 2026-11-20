from types import SimpleNamespace

import httpx
import pytest

from api.contexts.access.dependencies import current_user
from api.contexts.presentation.fragments import fetch
from api.db import get_session
from api.main import create_app


@pytest.fixture
async def mute_client(integration_session):
    users = await fetch(
        integration_session,
        'INSERT INTO "user" (password,is_superuser,first_name,last_name,is_staff,is_active,'
        "date_joined,email,is_email_verified,created_at) "
        "SELECT '',false,'','',false,true,now(),email,true,now() "
        "FROM unnest(ARRAY['mute-author@example.test','mute-target@example.test']) AS email "
        "RETURNING id",
        {},
    )
    author, target = [user.id for user in users]

    async def database():
        yield integration_session

    app = create_app()
    app.dependency_overrides[get_session] = database
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(id=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield integration_session, client, author, target


@pytest.mark.asyncio
async def test_mute_updates_lists_and_removes_idempotently(mute_client):
    session, client, _, target = mute_client
    path = f"/api/v1/community/me/mutes/{target}/"
    created = await client.put(path, json={"reason": "  first reason  "})
    assert created.status_code == 201, created.text
    assert created.json()["reason"] == "first reason"
    original_time = created.json()["created_at"]
    unchanged = await client.put(path, json={})
    assert unchanged.status_code == 200 and unchanged.json()["reason"] == "first reason"
    updated = await client.put(path, json={"reason": "updated"})
    assert updated.status_code == 200 and updated.json()["reason"] == "updated"
    assert updated.json()["created_at"] == original_time
    listed = await client.get("/api/v1/community/me/mutes/")
    assert listed.status_code == 200 and listed.json()["count"] == 1
    assert listed.json()["results"] == [updated.json()]
    for _ in range(2):
        assert (await client.delete(path)).status_code == 204
    assert (await fetch(session, "SELECT count(*) AS n FROM community_user_mute", {}))[0].n == 0


@pytest.mark.asyncio
async def test_cannot_mute_self_and_missing_users_are_404(mute_client):
    _, client, author, _ = mute_client
    self_mute = await client.put(f"/api/v1/community/me/mutes/{author}/", json={})
    assert self_mute.status_code == 400
    assert self_mute.json()["code"] == "community.cannot_mute_self"
    missing = "/api/v1/community/me/mutes/9223372036854775807/"
    assert (await client.put(missing, json={})).status_code == 404
    assert (await client.delete(missing)).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["mutes", "blocks"])
@pytest.mark.parametrize(
    "reason,message",
    [
        (None, "This field may not be null."),
        (True, "Not a valid string."),
        ({}, "Not a valid string."),
        ("x" * 257, "Ensure this field has no more than 256 characters."),
    ],
)
async def test_relationship_reason_validation_uses_existing_errors(
    mute_client, kind, reason, message
):
    _, client, _, target = mute_client
    response = await client.put(f"/api/v1/community/me/{kind}/{target}/", json={"reason": reason})
    assert response.status_code == 400, response.text
    assert response.json()["errors"] == {"reason": [message]}
