"""Which social sign-in buttons the frontend should render."""

import os
import secrets
from typing import Any

from fastapi import APIRouter

from api.contexts.access.security import create_tokens
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/social/github/start/")
async def github_start(redirect: str = "") -> dict[str, str]:
    from api.config import settings
    from api.contexts.access import oauth

    if not oauth.is_configured():
        raise ProblemError(
            status_code=503,
            detail="This sign-in provider is not configured.",
            code="users.social_login_unavailable",
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


@router.get("/social/github/callback/")
async def github_callback(
    state: str = "",
    code: str = "",
    session: SessionDep = None,  # type: ignore[assignment]
) -> Any:
    from fastapi.responses import RedirectResponse

    from api.config import settings
    from api.contexts.access import oauth

    frontend = os.environ.get("FRONTEND_SITE_URL", "").rstrip("/")
    body = oauth.read_state(state, secret=settings.jwt_secret)
    if body is None or not code:
        return RedirectResponse(f"{frontend}/login", status_code=302)
    try:
        profile = await oauth.fetch_profile(code)
    except Exception:
        return RedirectResponse(f"{frontend}/login", status_code=302)
    user_id, password_hash, redirect = await _social_login(session, profile, body)
    _access, refresh = create_tokens(
        user_id=user_id,
        password_hash=password_hash,
        secret=settings.jwt_secret,
        access_seconds=settings.access_token_seconds,
        refresh_seconds=settings.refresh_token_seconds,
    )
    response = RedirectResponse(f"{frontend}{_safe_path(redirect)}", status_code=302)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh,
        max_age=settings.refresh_token_seconds,
        path=settings.refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )
    del _access
    return response


def _safe_path(value: Any) -> str:
    text = str(value or "/")
    if not text.startswith("/") or text.startswith("//"):
        return "/"
    return text


async def _social_login(
    session: Any, profile: dict[str, Any], state: dict[str, Any]
) -> tuple[int, str, str]:
    from api.contexts.access.security import hash_password
    from api.contexts.presentation.fragments import fetch

    identity = await fetch(
        session,
        "SELECT user_id FROM social_identity WHERE provider = :provider AND subject = :subject",
        {"provider": profile["provider"], "subject": profile["subject"]},
    )
    if identity:
        await fetch(
            session,
            "UPDATE social_identity SET handle = :handle, email = :email,"
            " avatar_url = :avatar WHERE provider = :provider"
            " AND subject = :subject RETURNING id",
            {
                "handle": profile["handle"],
                "email": profile["email"],
                "avatar": profile["avatar_url"],
                "provider": profile["provider"],
                "subject": profile["subject"],
            },
        )
        rows = await fetch(
            session, 'SELECT id, password FROM "user" WHERE id = :id', {"id": identity[0].user_id}
        )
        await session.commit()
        return rows[0].id, rows[0].password, str(state.get("redirect") or "/")
    existing = await fetch(
        session,
        'SELECT id, password FROM "user" WHERE lower(email) = :email',
        {"email": profile["email"].lower()},
    )
    if existing:
        user_id, password_hash = existing[0].id, existing[0].password
    else:
        password_hash = hash_password(secrets.token_urlsafe(32))
        created = await fetch(
            session,
            'INSERT INTO "user" (password, is_superuser, first_name, last_name,'
            " is_staff, is_active, date_joined, email, is_email_verified, created_at)"
            " VALUES (:password, false, '', '', false, true, now(), :email, true, now())"
            " RETURNING id",
            {"password": password_hash, "email": profile["email"]},
        )
        user_id = created[0].id
        nickname = profile["handle"] or profile["email"].split("@")[0]
        await fetch(
            session,
            "INSERT INTO user_profile (nickname, avatar, bio, theme_color, language,"
            " appearance, show_adult_content, user_id)"
            " VALUES (:nickname, :avatar, '', '#7F6FB0', 'auto', 'auto', false, :user_id)"
            " RETURNING id",
            {"nickname": nickname[:32], "avatar": profile["avatar_url"], "user_id": user_id},
        )
    await fetch(
        session,
        "INSERT INTO social_identity (user_id, provider, subject, handle, email,"
        " avatar_url, created_at) VALUES (:user_id, :provider, :subject, :handle,"
        " :email, :avatar, now()) RETURNING id",
        {
            "user_id": user_id,
            "provider": profile["provider"],
            "subject": profile["subject"],
            "handle": profile["handle"],
            "email": profile["email"],
            "avatar": profile["avatar_url"],
        },
    )
    await session.commit()
    return user_id, password_hash, str(state.get("redirect") or "/")
