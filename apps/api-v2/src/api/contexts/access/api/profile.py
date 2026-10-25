"""The signed-in user's own profile."""

import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError

from api.contexts.access.dependencies import current_user
from api.contexts.presentation.fragments import fetch
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/users", tags=["profile"])

DEFAULT_THEME = "#7F6FB0"
DEFAULT_LANGUAGE = "auto"
DEFAULT_APPEARANCE = "auto"


def _payload(profile: Any, user: Any) -> dict[str, Any]:
    return {
        "user_id": user.id,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "nickname": profile.nickname,
        "bio": profile.bio,
        "avatar": profile.avatar,
        "language": profile.language,
        "appearance": profile.appearance,
        "theme_color": profile.theme_color,
        "show_adult_content": profile.show_adult_content,
        "adult_content_confirmed_at": (
            profile.adult_content_confirmed_at.isoformat().replace("+00:00", "Z")
            if profile.adult_content_confirmed_at
            else None
        ),
    }


async def _free_nickname(session: SessionDep, user_id: int) -> str:
    base = f"user_{user_id}"
    taken = {
        row.nickname
        for row in await fetch(
            session,
            "SELECT nickname FROM user_profile WHERE nickname LIKE :pattern",
            {"pattern": f"{base}%"},
        )
    }
    for index in range(20):
        candidate = base if index == 0 else f"{base}_{index}"
        if candidate not in taken:
            return candidate
    return f"{base}_{user_id}"


async def _profile(session: SessionDep, user: Any) -> Any:
    rows = await fetch(
        session,
        "SELECT nickname, bio, avatar, language, appearance, theme_color,"
        " show_adult_content, adult_content_confirmed_at"
        " FROM user_profile WHERE user_id = :user_id",
        {"user_id": user.id},
    )
    if rows:
        return rows[0]
    nickname = await _free_nickname(session, user.id)
    try:
        async with session.begin_nested():
            rows = await fetch(
                session,
                """
                INSERT INTO user_profile (
                    nickname, avatar, bio, theme_color, user_id, language,
                    appearance, show_adult_content
                ) VALUES (
                    :nickname, '', '', :theme, :user_id, :language,
                    :appearance, false
                )
                RETURNING nickname, bio, avatar, language, appearance,
                          theme_color, show_adult_content,
                          adult_content_confirmed_at
                """,
                {
                    "nickname": nickname,
                    "theme": DEFAULT_THEME,
                    "user_id": user.id,
                    "language": DEFAULT_LANGUAGE,
                    "appearance": DEFAULT_APPEARANCE,
                },
            )
    except IntegrityError:
        rows = await fetch(
            session,
            "SELECT nickname, bio, avatar, language, appearance, theme_color,"
            " show_adult_content, adult_content_confirmed_at"
            " FROM user_profile WHERE user_id = :user_id",
            {"user_id": user.id},
        )
    await session.commit()
    return rows[0]


@router.get("/me/profile/")
async def my_profile(
    session: SessionDep, user: Annotated[Any, Depends(current_user)]
) -> dict[str, Any]:
    return _payload(await _profile(session, user), user)


INVALID_COLOR = "theme_color must be a hex color, e.g. #66ccff."
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """The same rules and messages the Django serializer answers with."""
    values: dict[str, Any] = {}
    errors: dict[str, list[str]] = {}
    if "nickname" in payload:
        nickname = payload["nickname"]
        if not isinstance(nickname, str):
            errors["nickname"] = ["Not a valid string."]
        elif not nickname.strip():
            errors["nickname"] = ["This field may not be blank."]
        elif len(nickname) > 32:
            errors["nickname"] = ["Ensure this field has no more than 32 characters."]
        else:
            values["nickname"] = nickname
    if "bio" in payload:
        bio = payload["bio"]
        if not isinstance(bio, str):
            errors["bio"] = ["Not a valid string."]
        elif len(bio) > 500:
            errors["bio"] = ["Ensure this field has no more than 500 characters."]
        else:
            values["bio"] = bio
    if "theme_color" in payload:
        color = payload["theme_color"]
        if not isinstance(color, str):
            errors["theme_color"] = ["Not a valid string."]
        elif color and not COLOR.match(color):
            errors["theme_color"] = [INVALID_COLOR]
        else:
            values["theme_color"] = color or DEFAULT_THEME
    return values, errors


@router.patch("/me/profile/")
async def update_profile(
    payload: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    values, errors = _validate(payload)
    if not values and not errors:
        errors["non_field_errors"] = ["No fields to update."]
    if errors:
        raise ProblemError(status_code=400, detail="Request validation failed.", errors=errors)
    profile = await _profile(session, user)
    assignments = ", ".join(f"{column} = :{column}" for column in values)
    try:
        async with session.begin_nested():
            rows = await fetch(
                session,
                f"UPDATE user_profile SET {assignments} WHERE user_id = :user_id"
                " RETURNING nickname, bio, avatar, language, appearance, theme_color,"
                " show_adult_content, adult_content_confirmed_at",
                {**values, "user_id": user.id},
            )
    except IntegrityError as error:
        raise ProblemError(
            status_code=409,
            detail="The nickname is already in use.",
            code="users.nickname_already_exists",
        ) from error
    await session.commit()
    return _payload(rows[0] if rows else profile, user)
