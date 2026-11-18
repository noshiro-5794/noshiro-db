import time

import httpx
import jwt
import pytest

from api.config import settings
from api.contexts.access.security import create_tokens
from api.contexts.presentation.fragments import fetch
from api.db import get_session
from api.main import create_app

SECRET = "logout-test-key-with-at-least-thirty-two-bytes"


@pytest.fixture
async def logout_client(integration_session, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", SECRET)

    async def database():
        yield integration_session

    app = create_app()
    app.dependency_overrides[get_session] = database
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield integration_session, client


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", ["invalid", True, str(2**80)])
async def test_logout_clears_malformed_signed_cookies_without_blacklist_writes(
    logout_client, user_id
):
    session, client = logout_client
    token = jwt.encode(
        {
            "token_type": "refresh",
            "user_id": user_id,
            "jti": "logout-test",
            "exp": int(time.time()) + 60,
        },
        SECRET,
        algorithm="HS256",
    )
    response = await client.post(
        "/api/v1/auth/session/", headers={"Cookie": f"{settings.refresh_cookie_name}={token}"}
    )
    assert response.status_code == 204 and "Max-Age=0" in response.headers["set-cookie"]
    assert (await fetch(session, "SELECT count(*) AS n FROM token_blacklist_outstandingtoken", {}))[
        0
    ].n == 0


@pytest.mark.asyncio
async def test_logout_blacklists_once_and_ignores_deleted_user_tokens(logout_client):
    session, client = logout_client
    user = (
        await fetch(
            session,
            'INSERT INTO "user" (password,is_superuser,first_name,last_name,is_staff,is_active,'
            "date_joined,email,is_email_verified,created_at) "
            "VALUES ('',false,'','',false,true,now(),'logout@example.test',true,now()) "
            "RETURNING id",
            {},
        )
    )[0].id
    _, token = create_tokens(
        user_id=user, password_hash="hash", secret=SECRET, access_seconds=60, refresh_seconds=60
    )
    for _ in range(2):
        response = await client.post(
            "/api/v1/auth/session/", headers={"Cookie": f"{settings.refresh_cookie_name}={token}"}
        )
        assert response.status_code == 204
    assert (await fetch(session, "SELECT count(*) AS n FROM token_blacklist_blacklistedtoken", {}))[
        0
    ].n == 1
    missing = jwt.encode(
        {
            "user_id": str(2**60),
            "token_type": "refresh",
            "jti": "missing-user",
            "exp": int(time.time()) + 60,
        },
        SECRET,
        algorithm="HS256",
    )
    response = await client.post(
        "/api/v1/auth/session/", headers={"Cookie": f"{settings.refresh_cookie_name}={missing}"}
    )
    assert response.status_code == 204
