"""Notification counts and the read cursor.

Small on purpose: the list endpoint belongs with the feed work, but the badge in
the header only needs a count and a way to clear it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.community.people import person
from api.contexts.presentation.fragments import fetch


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


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


NOTIFICATION_QUERY = """
    SELECT notification.id, notification.notification_type, notification.metadata,
           notification.read_at, notification.created_at,
           actor.id AS actor_id, actor_profile.nickname AS actor_nickname,
           actor_profile.avatar AS actor_avatar,
           activity.id AS activity_id,
           activity_user.id AS activity_user_id,
           activity_user_profile.nickname AS activity_user_nickname,
           activity_user_profile.avatar AS activity_user_avatar,
           activity_target.id AS activity_target_id,
           activity_target_profile.nickname AS activity_target_nickname,
           activity_target_profile.avatar AS activity_target_avatar
    FROM community_notification AS notification
    LEFT JOIN "user" AS actor ON actor.id = notification.actor_id
    LEFT JOIN user_profile AS actor_profile ON actor_profile.user_id = actor.id
    LEFT JOIN community_activity AS activity ON activity.id = notification.activity_id
    LEFT JOIN "user" AS activity_user ON activity_user.id = activity.user_id
    LEFT JOIN user_profile AS activity_user_profile
      ON activity_user_profile.user_id = activity_user.id
    LEFT JOIN "user" AS activity_target ON activity_target.id = activity.target_user_id
    LEFT JOIN user_profile AS activity_target_profile
      ON activity_target_profile.user_id = activity_target.id
"""


async def read_one(session: AsyncSession, *, user_id: int, notification_id: int) -> dict[str, Any]:
    rows = await fetch(
        session,
        NOTIFICATION_QUERY
        + " WHERE notification.id = :id AND notification.recipient_id = :user_id",
        {"id": notification_id, "user_id": user_id},
    )
    if not rows:
        raise LookupError(notification_id)
    row = rows[0]
    if row.read_at is None:
        updated = await fetch(
            session,
            "UPDATE community_notification SET read_at = now()"
            " WHERE id = :id AND read_at IS NULL RETURNING read_at",
            {"id": notification_id},
        )
        await session.commit()
        read_at = updated[0].read_at if updated else row.read_at
    else:
        read_at = row.read_at
    target = None
    if row.activity_id is not None:
        target = {
            "type": "activity",
            "id": row.activity_id,
            "user": person(
                row.activity_user_id,
                row.activity_user_nickname,
                row.activity_user_avatar,
            ),
            "target_user": person(
                row.activity_target_id,
                row.activity_target_nickname,
                row.activity_target_avatar,
            ),
        }
    return {
        "id": row.id,
        "notification_type": row.notification_type,
        "actor": person(row.actor_id, row.actor_nickname, row.actor_avatar),
        "target": target,
        "metadata": row.metadata,
        "is_read": read_at is not None,
        "read_at": _iso(read_at),
        "created_at": _iso(row.created_at),
    }
