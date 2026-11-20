"""Persisted refresh-token revocation shared by logout and rotation."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.contexts.access.security import REFRESH, create_tokens, revoke_token, session_claims
from api.db import fetch
from api.shared.problems import ProblemError


async def revoke_refresh_token(session: AsyncSession, token: str, claims: dict[str, Any]) -> None:
    users = await fetch(
        session,
        'SELECT id FROM "user" WHERE id=:id FOR UPDATE',
        {"id": int(claims["user_id"])},
    )
    if not users:
        return
    rows = await fetch(
        session,
        """
        INSERT INTO refresh_token (
            user_id, jti, token, created_at, expires_at
        ) VALUES (
            :user_id, :jti, :token, now(), to_timestamp(:expires_at)
        )
        ON CONFLICT (jti) DO NOTHING
        RETURNING id
        """,
        {
            "user_id": int(claims["user_id"]),
            "jti": claims["jti"],
            "token": token,
            "expires_at": claims["exp"],
        },
    )
    if not rows:
        rows = await fetch(
            session,
            "SELECT id FROM refresh_token WHERE jti = :jti",
            {"jti": claims["jti"]},
        )
    await fetch(
        session,
        """
        INSERT INTO refresh_token_revocation (token_id, revoked_at)
        VALUES (:token_id, now())
        ON CONFLICT (token_id) DO NOTHING
        RETURNING id
        """,
        {"token_id": rows[0].id},
    )


async def rotate_refresh_token(session: AsyncSession, token: str) -> tuple[str, str]:
    claims = session_claims(token, settings.jwt_secret, token_type=REFRESH)
    if claims is None:
        raise ProblemError(status_code=401, detail="Token is invalid", code="token_not_valid")
    # Serialize rotation and logout for this account before checking revocation.
    users = await fetch(
        session,
        'SELECT id, password, is_active FROM "user" WHERE id=:id FOR UPDATE',
        {"id": int(claims["user_id"])},
    )
    if not users:
        raise ProblemError(
            status_code=401, detail="Refresh token is invalid.", code="token_not_valid"
        )
    revoked = await fetch(
        session,
        "SELECT 1 FROM refresh_token_revocation AS revoked"
        " JOIN refresh_token AS issued ON issued.id=revoked.token_id"
        " WHERE issued.jti=:jti",
        {"jti": claims["jti"]},
    )
    if revoked:
        raise ProblemError(status_code=401, detail="Token is blacklisted", code="token_not_valid")
    user = users[0]
    if not user.is_active:
        raise ProblemError(
            status_code=401,
            detail="No active account found for the given token.",
            code="no_active_account",
        )
    fingerprint = claims.get("hash_password")
    if fingerprint is not None and fingerprint != revoke_token(user.password):
        raise ProblemError(
            status_code=401,
            detail="The user's password has been changed.",
            code="password_changed",
        )
    access, refresh = create_tokens(
        user_id=user.id,
        password_hash=user.password,
        secret=settings.jwt_secret,
        access_seconds=settings.access_token_seconds,
        refresh_seconds=settings.refresh_token_seconds,
        claims=claims,
    )
    await revoke_refresh_token(session, token, claims)
    new_claims = session_claims(refresh, settings.jwt_secret, token_type=REFRESH)
    assert new_claims is not None
    await fetch(
        session,
        "INSERT INTO refresh_token"
        " (user_id,jti,token,created_at,expires_at)"
        " VALUES (:user,:jti,:token,now(),to_timestamp(:expiry)) RETURNING id",
        {
            "user": user.id,
            "jti": new_claims["jti"],
            "token": refresh,
            "expiry": new_claims["exp"],
        },
    )
    await session.commit()
    return access, refresh
