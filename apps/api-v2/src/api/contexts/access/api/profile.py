"""The signed-in user's own profile."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError

from api.contexts.access.dependencies import current_user
from api.contexts.presentation.fragments import fetch
from api.db import SessionDep

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
