"""Email verification codes and the registration they unlock."""

from __future__ import annotations

import re
import secrets
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.config import settings
from api.contexts.access.security import create_tokens, hash_password
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

PURPOSES = ("register", "login", "reset_password")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODE_RE = re.compile(r"^\d{6}$")
MAX_ATTEMPTS = 5
CODE_TTL_MINUTES = 10


@router.post("/verification-codes/", status_code=202)
async def send_code(
    body: dict[str, Any],
    session: SessionDep,
) -> dict[str, str]:
    email = str(body.get("email", "")).strip().lower()
    purpose = body.get("purpose")
    errors: dict[str, list[str]] = {}
    if not EMAIL_RE.match(email):
        errors["email"] = ["Enter a valid email address."]
    if purpose not in PURPOSES:
        errors["purpose"] = [f'"{purpose}" is not a valid choice.']
    if errors:
        raise ProblemError(status_code=400, detail="Request validation failed.", errors=errors)
    code = f"{secrets.randbelow(1_000_000):06d}"
    await _insert(
        session,
        "INSERT INTO email_verification (email, code, purpose, is_used, attempts,"
        " expire_at, created_at) VALUES (:email, :code, :purpose, false, 0,"
        " now() + interval '10 minutes', now()) RETURNING id",
        {"email": email, "code": code, "purpose": purpose},
    )
    await session.commit()
    return {"status": "accepted"}


async def _insert(session: Any, sql: str, params: dict[str, Any]) -> Any:
    from api.contexts.presentation.fragments import fetch

    return await fetch(session, sql, params)


async def _verify(session: Any, *, email: str, purpose: str, code: str) -> Any:
    from api.contexts.presentation.fragments import fetch

    rows = await fetch(
        session,
        "SELECT id, code, attempts, expire_at FROM email_verification"
        " WHERE lower(email) = :email AND purpose = :purpose AND NOT is_used"
        " ORDER BY created_at DESC LIMIT 1",
        {"email": email, "purpose": purpose},
    )
    if not rows:
        raise ProblemError(status_code=400, detail="Invalid verification code.")
    row = rows[0]
    if row.attempts >= MAX_ATTEMPTS:
        raise ProblemError(status_code=400, detail="Invalid verification code.")
    if not secrets.compare_digest(str(row.code), code):
        await fetch(
            session,
            "UPDATE email_verification SET attempts = attempts + 1 WHERE id = :id RETURNING id",
            {"id": row.id},
        )
        await session.commit()
        raise ProblemError(status_code=400, detail="Invalid verification code.")
    return row


@router.post("/registrations/")
async def register(body: dict[str, Any], session: SessionDep) -> JSONResponse:
    from api.contexts.presentation.fragments import fetch

    email = str(body.get("email", "")).strip().lower()
    password = body.get("password")
    code = body.get("code")
    nickname = body.get("nickname")
    errors: dict[str, list[str]] = {}
    if not EMAIL_RE.match(email):
        errors["email"] = ["Enter a valid email address."]
    if not isinstance(password, str) or len(password) < 8:
        errors["password"] = ["This password is too short. It must contain at least 8 characters."]
    if not isinstance(code, str) or not CODE_RE.match(code):
        errors["code"] = ["This value does not match the required pattern."]
    nickname_text = nickname if isinstance(nickname, str) else ""
    if not 2 <= len(nickname_text) <= 32:
        errors["nickname"] = ["Ensure this field has between 2 and 32 characters."]
    if errors:
        raise ProblemError(status_code=400, detail="Request validation failed.", errors=errors)
    existing = await fetch(
        session, 'SELECT 1 FROM "user" WHERE lower(email) = :email', {"email": email}
    )
    if existing:
        raise ProblemError(status_code=409, detail="An account with this email exists.")
    taken = await fetch(
        session,
        "SELECT 1 FROM user_profile WHERE lower(nickname) = :nickname",
        {"nickname": nickname_text.strip().lower()},
    )
    if taken:
        raise ProblemError(
            status_code=409,
            detail="The nickname is already in use.",
            code="users.nickname_already_exists",
        )
    await _verify(session, email=email, purpose="register", code=str(code))
    encoded = hash_password(str(password))
    rows = await fetch(
        session,
        'INSERT INTO "user" (password, is_superuser, first_name, last_name, is_staff,'
        " is_active, date_joined, email, is_email_verified, created_at)"
        " VALUES (:password, false, '', '', false, true, now(), :email, true, now())"
        " RETURNING id",
        {"password": encoded, "email": email},
    )
    user_id = rows[0].id
    await fetch(
        session,
        "INSERT INTO user_profile (nickname, avatar, bio, theme_color, language,"
        " appearance, show_adult_content, user_id)"
        " VALUES (:nickname, '', '', '#7F6FB0', 'auto', 'auto', false, :user_id)"
        " RETURNING id",
        {"nickname": nickname_text, "user_id": user_id},
    )
    await fetch(
        session,
        "UPDATE email_verification SET is_used = true WHERE lower(email) = :email"
        " AND purpose = 'register' AND NOT is_used RETURNING id",
        {"email": email},
    )
    await session.commit()
    access, refresh = create_tokens(
        user_id=user_id,
        password_hash=encoded,
        secret=settings.jwt_secret,
        access_seconds=settings.access_token_seconds,
        refresh_seconds=settings.refresh_token_seconds,
    )
    response = JSONResponse({"access": access}, status_code=201)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh,
        max_age=settings.refresh_token_seconds,
        path=settings.refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )
    return response


@router.post("/sessions/code/")
async def code_login(body: dict[str, Any], session: SessionDep) -> JSONResponse:
    from api.contexts.presentation.fragments import fetch

    email = str(body.get("email", "")).strip().lower()
    code = body.get("code")
    if not EMAIL_RE.match(email) or not isinstance(code, str) or not CODE_RE.match(code):
        raise ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors={"code": ["This value does not match the required pattern."]},
        )
    await _verify(session, email=email, purpose="login", code=code)
    rows = await fetch(
        session,
        'SELECT id, password, is_active FROM "user" WHERE lower(email) = :email',
        {"email": email},
    )
    if not rows or not rows[0].is_active:
        raise ProblemError(
            status_code=401, detail="Invalid credentials.", code="users.invalid_credentials"
        )
    user = rows[0]
    await fetch(
        session,
        "UPDATE email_verification SET is_used = true WHERE lower(email) = :email"
        " AND purpose = 'login' AND NOT is_used RETURNING id",
        {"email": email},
    )
    await session.commit()
    access, refresh = create_tokens(
        user_id=user.id,
        password_hash=user.password,
        secret=settings.jwt_secret,
        access_seconds=settings.access_token_seconds,
        refresh_seconds=settings.refresh_token_seconds,
    )
    response = JSONResponse({"access": access})
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh,
        max_age=settings.refresh_token_seconds,
        path=settings.refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )
    return response


@router.post("/password-resets/", status_code=204)
async def reset_password(body: dict[str, Any], session: SessionDep) -> None:
    from api.contexts.presentation.fragments import fetch

    email = str(body.get("email", "")).strip().lower()
    code = body.get("code")
    new_password = body.get("new_password")
    errors: dict[str, list[str]] = {}
    if not EMAIL_RE.match(email):
        errors["email"] = ["Enter a valid email address."]
    if not isinstance(code, str) or not CODE_RE.match(code):
        errors["code"] = ["This value does not match the required pattern."]
    if not isinstance(new_password, str) or len(new_password) < 8:
        errors["new_password"] = [
            "This password is too short. It must contain at least 8 characters."
        ]
    if errors:
        raise ProblemError(status_code=400, detail="Request validation failed.", errors=errors)
    await _verify(session, email=email, purpose="reset_password", code=str(code))
    await fetch(
        session,
        'UPDATE "user" SET password = :password WHERE lower(email) = :email RETURNING id',
        {"password": hash_password(str(new_password)), "email": email},
    )
    await fetch(
        session,
        "UPDATE email_verification SET is_used = true"
        " WHERE lower(email) = :email AND purpose = 'reset_password' AND NOT is_used"
        " RETURNING id",
        {"email": email},
    )
    await session.commit()
