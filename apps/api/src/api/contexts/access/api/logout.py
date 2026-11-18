"""Ending a session.

The refresh token lives in an HttpOnly cookie, so ending the session means
blacklisting it and telling the browser to forget it. An expired or malformed
cookie is not an error: the session is over either way.
"""

from typing import Any

from fastapi import APIRouter, Request, Response

from api.config import settings
from api.contexts.access.security import REFRESH, session_claims
from api.contexts.presentation.fragments import fetch
from api.db import SessionDep

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def _blacklist(session: SessionDep, token: str, claims: dict[str, Any]) -> None:
    users = await fetch(
        session,
        'SELECT id FROM "user" WHERE id=:id FOR KEY SHARE',
        {"id": int(claims["user_id"])},
    )
    if not users:
        return
    rows = await fetch(
        session,
        """
        INSERT INTO token_blacklist_outstandingtoken (
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
            "SELECT id FROM token_blacklist_outstandingtoken WHERE jti = :jti",
            {"jti": claims["jti"]},
        )
    await fetch(
        session,
        """
        INSERT INTO token_blacklist_blacklistedtoken (token_id, blacklisted_at)
        VALUES (:token_id, now())
        ON CONFLICT (token_id) DO NOTHING
        RETURNING id
        """,
        {"token_id": rows[0].id},
    )
    await session.commit()


@router.post("/session/", status_code=204)
async def logout(request: Request, session: SessionDep) -> Response:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        claims = session_claims(raw, settings.jwt_secret, token_type=REFRESH)
        if claims is not None:
            await _blacklist(session, raw, claims)
    response = Response(status_code=204)
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        samesite=settings.refresh_cookie_samesite,
    )
    return response
