"""Visibility of another account's public resources."""

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.shared.problems import ProblemError


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
