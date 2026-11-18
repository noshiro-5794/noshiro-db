from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from api.contexts.access.dependencies import current_user, optional_user, staff_user
from api.contexts.presentation.fragments import fetch
from api.db import get_session
from api.main import create_app
from api.shared.cursor import Cursor, encode
from api.worker import jobs


@pytest.fixture
async def cursor_client(integration_session):
    session = integration_session
    user_id = (
        await fetch(
            session,
            'INSERT INTO "user" (password,is_superuser,first_name,last_name,is_staff,is_active,'
            "date_joined,email,is_email_verified,created_at) "
            "VALUES ('',false,'','',true,true,now(),'cursor@example.test',true,now()) RETURNING id",
            {},
        )
    )[0].id
    for index in range(8):
        timestamp = datetime(2026, 11, 18, tzinfo=UTC) - timedelta(hours=index // 3)
        await fetch(
            session,
            "INSERT INTO community_activity "
            "(user_id,activity_type,message,visibility,feed_policy,group_key,"
            "dedupe_key,metadata,created_at) "
            "VALUES (:user,'followed','','public','normal','','','{}',:created) RETURNING id",
            {"user": user_id, "created": timestamp},
        )
        await fetch(
            session,
            "INSERT INTO community_notification "
            "(recipient_id,notification_type,metadata,created_at) "
            "VALUES (:user,'followed','{}',:created) RETURNING id",
            {"user": user_id, "created": timestamp},
        )
        identifier = await jobs.create_job(session, job_type="mal_import")
        await fetch(
            session,
            "UPDATE sync_job SET created_at=:created WHERE id=:id RETURNING id",
            {"id": identifier, "created": timestamp},
        )

    app = create_app()

    async def database():
        yield session

    async def viewer():
        return SimpleNamespace(id=user_id, is_staff=True)

    app.dependency_overrides[get_session] = database
    for dependency in [current_user, optional_user, staff_user]:
        app.dependency_overrides[dependency] = viewer
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield session, user_id, client


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["public", "mine", "user", "feed", "notifications", "jobs"])
async def test_http_cursor_pages_keep_ties_and_support_previous_links(cursor_client, kind):
    session, user_id, client = cursor_client
    paths = {
        "public": "/api/v1/community/activities/?page_size=2",
        "mine": "/api/v1/community/me/activities/?page_size=2",
        "user": f"/api/v1/community/users/{user_id}/activities/?page_size=2",
        "feed": "/api/v1/community/me/feed/?page_size=2&include_self=true",
        "notifications": "/api/v1/community/me/notifications/?page_size=2",
        "jobs": "/api/v1/operations/import-jobs/?page_size=2&provider=mal",
    }
    table = {"notifications": "community_notification", "jobs": "sync_job"}.get(
        kind, "community_activity"
    )
    expected = [
        str(row.id)
        for row in await fetch(
            session, f"SELECT id FROM {table} ORDER BY created_at DESC,id DESC", {}
        )
    ]
    first = await client.get(paths[kind])
    assert first.status_code == 200, first.text
    first = first.json()
    assert first["previous"] is None and first["next"] is not None
    second = (await client.get(first["next"])).json()
    assert second["previous"] is not None
    backward = (await client.get(second["previous"])).json()
    assert backward["results"] == first["results"]
    visited = []
    page = first
    for _ in range(8):
        visited.extend(str(row["id"]) for row in page["results"])
        if page["next"] is None:
            break
        response = await client.get(page["next"])
        assert response.status_code == 200, response.text
        page = response.json()
    assert visited == expected and len(visited) == 8
    invalid = await client.get(paths[kind] + "&cursor=" + encode(Cursor(position="invalid-date")))
    assert invalid.status_code == 404 and invalid.json()["detail"] == "Invalid cursor."
