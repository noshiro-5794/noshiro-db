"""Which social sign-in buttons the frontend should render."""

import os
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
