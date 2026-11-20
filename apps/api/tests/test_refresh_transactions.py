import asyncio
import os
import time
from http.cookies import SimpleCookie
from uuid import uuid4

import httpx
import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.config import settings
from api.contexts.access import sessions
from api.contexts.access.security import revoke_token
from api.contexts.presentation.fragments import fetch
from api.db import get_session
from api.main import create_app

SECRET = "refresh-test-key-with-at-least-thirty-two-bytes"
PATH = "/api/v1/auth/sessions/refresh/"


@pytest.fixture
async def refresh_client(integration_session, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", SECRET)
    user = (
        await fetch(
            integration_session,
            'INSERT INTO "user" (password,is_superuser,first_name,last_name,is_staff,is_active,'
            "date_joined,email,is_email_verified,created_at) "
            "VALUES ('stored-password',false,'','',false,true,now(),"
            "'refresh@example.test',true,now()) "
            "RETURNING id",
            {},
        )
    )[0].id
    await integration_session.commit()

    async def database():
        try:
            yield integration_session
        except Exception:
            await integration_session.rollback()
            raise

    app = create_app()
    app.dependency_overrides[get_session] = database
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield integration_session, client, user


def token_for(user, **changes):
    claims = {
        "token_type": "refresh",
        "user_id": str(user),
        "jti": "existing-refresh",
        "exp": int(time.time()) + 3600,
        "hash_password": revoke_token("stored-password"),
        "custom_claim": "retained",
    }
    claims.update(changes)
    return jwt.encode(claims, SECRET, algorithm="HS256")


async def refresh(client, token):
    return await client.post(PATH, headers={"Cookie": f"{settings.refresh_cookie_name}={token}"})


@pytest.mark.asyncio
async def test_refresh_rotates_and_rejects_replay_then_logout(refresh_client):
    session, client, user = refresh_client
    original = token_for(user)
    response = await refresh(client, original)
    assert response.status_code == 200, response.text
    access = jwt.decode(response.json()["access"], SECRET, algorithms=["HS256"])
    rotated = SimpleCookie(response.headers["set-cookie"])[settings.refresh_cookie_name].value
    claims = jwt.decode(rotated, SECRET, algorithms=["HS256"])
    assert access["token_type"] == "access" and claims["token_type"] == "refresh"
    assert access["custom_claim"] == claims["custom_claim"] == "retained"
    assert access["jti"] != claims["jti"] != "existing-refresh"
    assert claims["hash_password"] == revoke_token("stored-password")
    assert (await fetch(session, "SELECT count(*) AS n FROM refresh_token", {}))[0].n == 2
    replay = await refresh(client, original)
    assert replay.status_code == 401 and replay.json()["code"] == "token_not_valid"
    again = await refresh(client, rotated)
    assert again.status_code == 200
    latest = SimpleCookie(again.headers["set-cookie"])[settings.refresh_cookie_name].value
    logged_out = await client.post(
        "/api/v1/auth/session/", headers={"Cookie": f"{settings.refresh_cookie_name}={latest}"}
    )
    assert logged_out.status_code == 204
    assert (await refresh(client, latest)).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"user_id": "invalid"},
        {"user_id": str(2**80)},
        {"exp": 1},
        {"exp": 2**80},
        {"jti": "x" * 256},
        {"jti": ""},
        {"token_type": "access"},
    ],
)
async def test_unusable_refresh_claims_reject_without_writes(refresh_client, changes):
    session, client, user = refresh_client
    response = await refresh(client, token_for(user, **changes))
    assert response.status_code == 401, response.text
    assert (await fetch(session, "SELECT count(*) AS n FROM refresh_token", {}))[0].n == 0


@pytest.mark.asyncio
async def test_missing_cookie_and_missing_account(refresh_client):
    _, client, _ = refresh_client
    missing = await client.post(PATH)
    assert missing.status_code == 401
    assert missing.json()["detail"] == "refresh token cookie is missing"
    assert (await refresh(client, token_for(2**60))).status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_and_changed_password_cannot_refresh(refresh_client):
    session, client, user = refresh_client
    token = token_for(user)
    await fetch(
        session, 'UPDATE "user" SET is_active=false WHERE id=:id RETURNING id', {"id": user}
    )
    assert (await refresh(client, token)).json()["code"] == "no_active_account"
    await fetch(
        session,
        'UPDATE "user" SET is_active=true,password=:password WHERE id=:id RETURNING id',
        {"id": user, "password": "changed-password"},
    )
    assert (await refresh(client, token)).json()["code"] == "password_changed"


@pytest.mark.asyncio
async def test_pre_fingerprint_tokens_get_current_password_fingerprint(refresh_client):
    _, client, user = refresh_client
    claims = jwt.decode(token_for(user), SECRET, algorithms=["HS256"])
    claims.pop("hash_password")
    claims["exp"] = str(claims["exp"])
    response = await refresh(client, jwt.encode(claims, SECRET, algorithm="HS256"))
    assert response.status_code == 200, response.text
    access = jwt.decode(response.json()["access"], SECRET, algorithms=["HS256"])
    assert access["hash_password"] == revoke_token("stored-password")


@pytest.mark.asyncio
async def test_failed_replacement_insert_rolls_back_revocation(refresh_client, monkeypatch):
    session, client, user = refresh_client
    real_fetch = sessions.fetch

    async def fail_replacement(session, query, parameters):
        if query.startswith("INSERT INTO refresh_token"):
            raise RuntimeError("replacement insert failed")
        return await real_fetch(session, query, parameters)

    monkeypatch.setattr(sessions, "fetch", fail_replacement)
    with pytest.raises(RuntimeError, match="replacement insert failed"):
        await refresh(client, token_for(user))
    assert (await fetch(session, "SELECT count(*) AS n FROM refresh_token_revocation", {}))[
        0
    ].n == 0


@pytest.mark.asyncio
async def test_concurrent_refresh_consumes_the_token_once(integration_session, monkeypatch):
    # The integration fixture validates the disposable database before this case
    # creates committed rows visible to independent request connections.
    monkeypatch.setattr(settings, "jwt_secret", SECRET)
    engine = create_async_engine(
        os.environ["NOSHIRO_INTEGRATION_DATABASE_URL"].replace(
            "postgresql://", "postgresql+asyncpg://", 1
        ),
        poolclass=NullPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = None
    try:
        async with factory() as session:
            user_id = (
                await fetch(
                    session,
                    'INSERT INTO "user" (password,is_superuser,first_name,last_name,is_staff,'
                    "is_active,date_joined,email,is_email_verified,created_at) "
                    "VALUES ('stored-password',false,'','',false,true,now(),:email,true,now()) "
                    "RETURNING id",
                    {"email": f"refresh-{uuid4()}@example.test"},
                )
            )[0].id
            await session.commit()

        async def database():
            async with factory() as session:
                yield session

        app = create_app()
        app.dependency_overrides[get_session] = database
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            token = token_for(user_id, jti=str(uuid4()))
            responses = await asyncio.gather(refresh(client, token), refresh(client, token))
            assert sorted(response.status_code for response in responses) == [200, 401]
        async with factory() as session:
            counts = await fetch(
                session,
                "SELECT count(*) AS n FROM refresh_token WHERE user_id=:id",
                {"id": user_id},
            )
            assert counts[0].n == 2
    finally:
        if user_id is not None:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "DELETE FROM refresh_token_revocation WHERE token_id IN "
                        "(SELECT id FROM refresh_token WHERE user_id=:id)"
                    ),
                    {"id": user_id},
                )
                await connection.execute(
                    text("DELETE FROM refresh_token WHERE user_id=:id"),
                    {"id": user_id},
                )
                await connection.execute(text('DELETE FROM "user" WHERE id=:id'), {"id": user_id})
        await engine.dispose()
