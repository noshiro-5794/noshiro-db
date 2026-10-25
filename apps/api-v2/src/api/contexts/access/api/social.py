"""Which social sign-in buttons the frontend should render."""

import os
from typing import Any

from fastapi import APIRouter

from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/social/github/start/")
async def github_start(redirect: str = "") -> dict[str, str]:
    from api.config import settings
    from api.contexts.access import oauth

    if not oauth.is_configured():
        raise ProblemError(
            status_code=503,
            detail="Social sign-in is not available.",
            code="users.social_unavailable",
        )
    state = oauth.build_state(redirect, secret=settings.jwt_secret)
    return {"authorize_url": oauth.authorize_url(state)}


@router.get("/social/providers/")
async def providers() -> list[dict[str, Any]]:
    enabled = bool(
        os.environ.get("GITHUB_OAUTH_CLIENT_ID") and os.environ.get("GITHUB_OAUTH_CLIENT_SECRET")
    )
    return [
        {
            "provider": "github",
            "enabled": enabled,
            "authorize_path": "/api/v1/auth/social/github/start/",
        }
    ]
