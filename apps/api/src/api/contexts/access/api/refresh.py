"""Rotate the browser's refresh token and issue its next access token."""

from fastapi import APIRouter, Request, Response

from api.config import settings
from api.contexts.access.cookies import set_refresh_cookie
from api.contexts.access.rate_limits import limited
from api.contexts.access.sessions import rotate_refresh_token
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/sessions/refresh/", **limited("refresh"))
async def refresh_session(
    request: Request, response: Response, session: SessionDep
) -> dict[str, str]:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise ProblemError(status_code=401, detail="refresh token cookie is missing")
    access, refresh = await rotate_refresh_token(session, token)
    set_refresh_cookie(response, refresh)
    return {"access": access}
