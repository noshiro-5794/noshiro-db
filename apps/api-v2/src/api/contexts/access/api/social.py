"""Which social sign-in buttons the frontend should render."""

from fastapi import APIRouter

from api.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/social/providers/")
async def social_providers() -> list[dict[str, object]]:
    return [
        {
            "provider": "github",
            "enabled": bool(settings.github_client_id and settings.github_client_secret),
            "authorize_path": "/api/v1/auth/social/github/start/",
        }
    ]
