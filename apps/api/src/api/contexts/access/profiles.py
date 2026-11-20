"""Profile state and access to another account's public resources."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch
from api.shared.problems import ProblemError

DEFAULT_THEME = "#7F6FB0"
DEFAULT_LANGUAGE = "auto"
DEFAULT_APPEARANCE = "auto"
PROFILE_COLUMNS = (
    "nickname,bio,avatar,language,appearance,theme_color,"
    "show_adult_content,adult_content_confirmed_at"
)


async def get_or_create_profile(session: AsyncSession, *, user_id: int) -> Any:
    rows = await fetch(
        session,
        f"SELECT {PROFILE_COLUMNS} FROM user_profile WHERE user_id=:user",
        {"user": user_id},
    )
    if rows:
        return rows[0]
    base = f"user_{user_id}"
    for index in range(20):
        nickname = base if index == 0 else f"{base}_{index}"
        rows = await fetch(
            session,
            "INSERT INTO user_profile(nickname,avatar,bio,theme_color,user_id,language,"
            "appearance,show_adult_content)"
            f" VALUES (:nickname,'','',:theme,:user,:language,:appearance,false)"
            f" ON CONFLICT DO NOTHING RETURNING {PROFILE_COLUMNS}",
            {
                "nickname": nickname,
                "theme": DEFAULT_THEME,
                "user": user_id,
                "language": DEFAULT_LANGUAGE,
                "appearance": DEFAULT_APPEARANCE,
            },
        )
        if not rows:
            rows = await fetch(
                session,
                f"SELECT {PROFILE_COLUMNS} FROM user_profile WHERE user_id=:user",
                {"user": user_id},
            )
        if rows:
            await session.commit()
            return rows[0]
    raise RuntimeError("Could not create a unique default profile nickname.")


async def ensure_public_user(session: AsyncSession, *, user_id: int, viewer_id: int) -> None:
    rows = await fetch(
        session,
        'SELECT id FROM "user" WHERE id=:user AND NOT EXISTS ('
        " SELECT 1 FROM community_user_block"
        " WHERE (user_id=:viewer AND blocked_user_id=:user)"
        " OR (user_id=:user AND blocked_user_id=:viewer))",
        {"user": user_id, "viewer": viewer_id},
    )
    if not rows:
        raise ProblemError(status_code=404, detail="User not found.")
