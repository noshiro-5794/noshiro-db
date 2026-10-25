from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel

from api.config import settings
from api.contexts.access.security import create_tokens, verify_password
from api.contexts.presentation.fragments import fetch
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

INVALID = "The email address or password is invalid."


class PasswordLogin(BaseModel):
    email: str
    password: str


async def _user(session: SessionDep, email: str) -> Any:
    rows = await fetch(
        session,
        'SELECT id, email, password, is_active FROM "user" WHERE email = :email',
        {"email": email},
    )
    if rows:
        return rows[0]
    # Accounts created before email normalization was enforced still log in.
    return None


async def _user_case_insensitive(session: SessionDep, email: str) -> Any:
    rows = await fetch(
        session,
        'SELECT id, email, password, is_active FROM "user"'
        " WHERE lower(email) = lower(:email) LIMIT 1",
        {"email": email},
    )
    return rows[0] if rows else None


@router.post("/sessions/password/")
async def password_login(
    payload: PasswordLogin, response: Response, session: SessionDep
) -> dict[str, str]:
    user = await _user(session, payload.email)
    if user is None:
        candidate = await _user_case_insensitive(session, payload.email)
        if (
            candidate is not None
            and candidate.email != payload.email
            and verify_password(candidate.password, payload.password)
        ):
            user = candidate
    if user is None or not user.is_active or not verify_password(user.password, payload.password):
        raise ProblemError(status_code=401, detail=INVALID, code="users.invalid_credentials")
    access, refresh = create_tokens(
        user_id=user.id,
        password_hash=user.password,
        secret=settings.jwt_secret,
        access_seconds=settings.access_token_seconds,
        refresh_seconds=settings.refresh_token_seconds,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh,
        max_age=settings.refresh_token_seconds,
        path=settings.refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )
    return {"access": access}
