import time
from contextlib import asynccontextmanager

import jwt
import pytest

from api.contexts.presentation.fragments import fetch
from api.mcp import auth


@pytest.mark.asyncio
async def test_mcp_jwt_verifies_active_users_and_rejects_invalid_claims(
    integration_session, monkeypatch
):
    session = integration_session
    secret = "mcp-test-key-with-at-least-thirty-two-bytes"
    monkeypatch.setattr(auth.settings, "jwt_secret", secret)

    @asynccontextmanager
    async def scope():
        yield session

    monkeypatch.setattr(auth, "session_scope", scope)
    user = (
        await fetch(
            session,
            'INSERT INTO "user" (password,is_superuser,first_name,last_name,is_staff,is_active,'
            "date_joined,email,is_email_verified,created_at) "
            "VALUES ('',false,'','',false,true,now(),'mcp-auth@example.test',true,now()) "
            "RETURNING id",
            {},
        )
    )[0].id
    claims = {
        "user_id": str(user),
        "exp": int(time.time()) + 60,
        "jti": "test",
        "token_type": "access",
    }
    verifier = auth.TokenVerifier()
    token = jwt.encode(claims, secret, algorithm="HS256")
    verified = await verifier.verify_token(token)
    assert verified.subject == str(user) and verified.scopes == ["knowledge:read"]
    for update in [
        {"token_type": "refresh"},
        {"exp": 1},
        {"user_id": True},
        {"user_id": "invalid"},
        {"user_id": str(2**80)},
        {"user_id": "1.5"},
    ]:
        invalid = jwt.encode({**claims, **update}, secret, algorithm="HS256")
        assert await verifier.verify_token(invalid) is None
    await fetch(
        session, 'UPDATE "user" SET is_active=false WHERE id=:id RETURNING id', {"id": user}
    )
    assert await verifier.verify_token(token) is None
