import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import jwt
import pytest

from api.contexts.access import dependencies, security
from api.db import get_session
from api.main import create_app
from api.shared.problems import ProblemError

SECRET = "test-access-key-with-at-least-thirty-two-bytes"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id", [None, True, False, "invalid", "1.5", 1.5, "0", "-1", str(2**80), []]
)
async def test_malformed_token_subject_is_rejected_before_database_binding(monkeypatch, user_id):
    monkeypatch.setattr(dependencies.settings, "jwt_secret", SECRET)
    lookup = AsyncMock()
    monkeypatch.setattr(dependencies, "_user_for", lookup)
    token = jwt.encode(
        {
            "token_type": "access",
            "user_id": user_id,
            "jti": "test",
            "exp": int(time.time()) + 60,
        },
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(ProblemError) as caught:
        await dependencies.current_user(object(), "Bearer " + token)
    assert caught.value.status_code == 401 and caught.value.code == "token_not_valid"
    assert await dependencies.optional_user(object(), "Bearer " + token) is None
    lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_unconfigured_signing_key_rejects_access_before_lookup(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "jwt_secret", "")
    lookup = AsyncMock()
    monkeypatch.setattr(dependencies, "_user_for", lookup)
    with pytest.raises(ProblemError) as caught:
        await dependencies.current_user(object(), "Bearer invalid")
    assert caught.value.status_code == 401
    lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_access_token_retains_active_user_and_password_revocation_checks(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "jwt_secret", SECRET)
    user = SimpleNamespace(id=7, is_active=True, password="stored-password-hash")
    lookup = AsyncMock(return_value=user)
    monkeypatch.setattr(dependencies, "_user_for", lookup)
    token, _ = security.create_tokens(
        user_id=7, password_hash=user.password, secret=SECRET, access_seconds=60, refresh_seconds=60
    )
    assert await dependencies.current_user(object(), "Bearer " + token) is user
    user.password = "changed-password-hash"
    with pytest.raises(ProblemError) as caught:
        await dependencies.current_user(object(), "Bearer " + token)
    assert caught.value.status_code == 401
    lookup.assert_awaited_with(lookup.call_args.args[0], 7)


@pytest.mark.parametrize("missing", ["exp", "jti", "user_id", "token_type"])
def test_required_session_claims_are_enforced(missing):
    claims = {"token_type": "access", "user_id": "7", "jti": "test", "exp": int(time.time()) + 60}
    claims.pop(missing)
    assert security.session_claims(jwt.encode(claims, SECRET, algorithm="HS256"), SECRET) is None


def test_unconfigured_signing_key_rejects_access_tokens():
    assert security.session_claims("any-token", "") is None


@pytest.mark.asyncio
async def test_http_authentication_returns_problem_response_for_malformed_subject(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "jwt_secret", SECRET)
    lookup = AsyncMock()
    monkeypatch.setattr(dependencies, "_user_for", lookup)
    app = create_app()

    async def database():
        yield object()

    app.dependency_overrides[get_session] = database
    token = jwt.encode(
        {"token_type": "access", "user_id": "invalid", "jti": "test", "exp": int(time.time()) + 60},
        SECRET,
        algorithm="HS256",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/v1/users/me/profile/", headers={"Authorization": "Bearer " + token}
        )
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "token_not_valid"
    lookup.assert_not_awaited()
