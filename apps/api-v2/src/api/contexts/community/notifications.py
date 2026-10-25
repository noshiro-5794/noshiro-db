"""Notification counts and the read cursor.

Small on purpose: the list endpoint belongs with the feed work, but the badge in
the header only needs a count and a way to clear it.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


async def unread_count(session: AsyncSession, *, user_id: int) -> int:
    rows = await fetch(
        session,
        "SELECT count(*) AS total FROM community_notification"
        " WHERE recipient_id = :user_id AND read_at IS NULL",
        {"user_id": user_id},
    )
    return int(rows[0].total)


async def mark_all_read(session: AsyncSession, *, user_id: int) -> int:
    rows = await fetch(
        session,
        "UPDATE community_notification SET read_at = now()"
        " WHERE recipient_id = :user_id AND read_at IS NULL"
        " RETURNING id",
        {"user_id": user_id},
    )
    await session.commit()
    return len(rows)
