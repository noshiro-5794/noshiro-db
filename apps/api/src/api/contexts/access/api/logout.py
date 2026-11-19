"""Ending a session.

The refresh token lives in an HttpOnly cookie, so ending the session means
blacklisting it and telling the browser to forget it. An expired or malformed
cookie is not an error: the session is over either way.
"""

from fastapi import APIRouter, Request, Response

from api.config import settings
from api.contexts.access.cookies import clear_refresh_cookie
from api.contexts.access.security import REFRESH, session_claims
from api.contexts.access.sessions import blacklist_refresh_token
from api.db import SessionDep

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/session/", status_code=204)
async def logout(request: Request, session: SessionDep) -> Response:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        claims = session_claims(raw, settings.jwt_secret, token_type=REFRESH)
        if claims is not None:
            await blacklist_refresh_token(session, raw, claims)
            await session.commit()
    response = Response(status_code=204)
    clear_refresh_cookie(response)
    return response
