"""Who is asking.

A bearer token is accepted only when it is an access token, signed with the
service secret, and still matches the password it was minted against — the same
checks the Django service runs, so a token from either side is valid for both.
"""

from __future__ import annotations

from typing import Annotated, Any

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db import SessionDep
from api.shared.problems import ProblemError

from .security import ACCESS, revoke_token

MISSING = "Authentication credentials were not provided."
INVALID = "Given token not valid for any token type"


async def _user_for(session: AsyncSession, user_id: int) -> Any:
    from api.contexts.presentation.fragments import fetch

    rows = await fetch(
        session,
        'SELECT id, email, password, is_staff, is_superuser, is_active FROM "user" WHERE id = :id',
        {"id": user_id},
    )
    return rows[0] if rows else None


async def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Any:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ProblemError(status_code=401, detail=MISSING)
    token = authorization.split(" ", 1)[1]
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as error:
        raise ProblemError(status_code=401, detail=INVALID, code="token_not_valid") from error
    if claims.get("token_type") != ACCESS or not claims.get("user_id"):
        raise ProblemError(status_code=401, detail=INVALID, code="token_not_valid")
    user = await _user_for(session, int(claims["user_id"]))
    if (
        user is None
        or not user.is_active
        or claims.get("hash_password") != revoke_token(user.password)
    ):
        raise ProblemError(status_code=401, detail=INVALID, code="token_not_valid")
    return user


DENIED = "You do not have permission to perform this action."


async def staff_user(user: Annotated[Any, Depends(current_user)]) -> Any:
    if not user.is_staff:
        raise ProblemError(status_code=403, detail=DENIED)
    return user
