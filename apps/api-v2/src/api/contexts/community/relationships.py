"""Blocking and muting another account.

Blocking is not a single row: it removes the follow relations in both directions
and the mute this user had set, because a block that leaves a follow behind is
not a block.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

BLOCK_COLUMNS = (
    "block.id, block.reason, block.created_at, blocked.id AS user_id,"
    " blocked.email, profile.nickname, profile.avatar"
)
BLOCK_JOINS = """
    JOIN "user" AS blocked ON blocked.id = block.blocked_user_id
    LEFT JOIN user_profile AS profile ON profile.user_id = blocked.id
"""


def block_payload(row: Any) -> dict[str, Any]:
    return {
        "user": {
            "id": row.user_id,
            "nickname": row.nickname or "",
            "avatar": row.avatar or "",
        },
        "reason": row.reason,
        "created_at": _iso(row.created_at),
    }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


async def block_user(
    session: AsyncSession, *, user_id: int, target_user_id: int, reason: str
) -> tuple[dict[str, Any], bool]:
    target = await fetch(
        session,
        'SELECT id FROM "user" WHERE id = :id',
        {"id": target_user_id},
    )
    if not target:
        raise LookupError(target_user_id)
    existing = await fetch(
        session,
        f"SELECT {BLOCK_COLUMNS} FROM community_user_block AS block {BLOCK_JOINS}"
        " WHERE block.user_id = :user_id AND block.blocked_user_id = :target",
        {"user_id": user_id, "target": target_user_id},
    )
    created = not existing
    if existing and reason and existing[0].reason != reason:
        await fetch(
            session,
            "UPDATE community_user_block SET reason = :reason WHERE id = :id RETURNING id",
            {"reason": reason, "id": existing[0].id},
        )
    elif not existing:
        await fetch(
            session,
            "INSERT INTO community_user_block (user_id, blocked_user_id, reason,"
            " created_at) VALUES (:user_id, :target, :reason, now()) RETURNING id",
            {"user_id": user_id, "target": target_user_id, "reason": reason},
        )
    await fetch(
        session,
        "DELETE FROM community_user_follow WHERE (follower_id = :user_id"
        " AND following_id = :target) OR (follower_id = :target"
        " AND following_id = :user_id) RETURNING id",
        {"user_id": user_id, "target": target_user_id},
    )
    await fetch(
        session,
        "DELETE FROM community_user_mute"
        " WHERE user_id = :user_id AND muted_user_id = :target RETURNING id",
        {"user_id": user_id, "target": target_user_id},
    )
    rows = await fetch(
        session,
        f"SELECT {BLOCK_COLUMNS} FROM community_user_block AS block {BLOCK_JOINS}"
        " WHERE block.user_id = :user_id AND block.blocked_user_id = :target",
        {"user_id": user_id, "target": target_user_id},
    )
    await session.commit()
    return block_payload(rows[0]), created


async def unblock_user(session: AsyncSession, *, user_id: int, target_user_id: int) -> None:
    target = await fetch(session, 'SELECT id FROM "user" WHERE id = :id', {"id": target_user_id})
    if not target:
        raise LookupError(target_user_id)
    await fetch(
        session,
        "DELETE FROM community_user_block"
        " WHERE user_id = :user_id AND blocked_user_id = :target RETURNING id",
        {"user_id": user_id, "target": target_user_id},
    )
    await session.commit()


MUTE_COLUMNS = (
    "mute.id, mute.reason, mute.created_at, muted.id AS user_id,"
    " muted.email, profile.nickname, profile.avatar"
)
MUTE_JOINS = """
    JOIN "user" AS muted ON muted.id = mute.muted_user_id
    LEFT JOIN user_profile AS profile ON profile.user_id = muted.id
"""


async def _page(
    session: AsyncSession,
    *,
    table: str,
    alias: str,
    columns: str,
    joins: str,
    user_id: int,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM {table} WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    rows = await fetch(
        session,
        f"SELECT {columns} FROM {table} AS {alias} {joins}"
        f" WHERE {alias}.user_id = :user_id"
        f" ORDER BY {alias}.created_at DESC, {alias}.id DESC"
        " LIMIT :limit OFFSET :offset",
        {
            "user_id": user_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    return int(total[0].total), [block_payload(row) for row in rows]


async def list_blocks(
    session: AsyncSession, *, user_id: int, page: int, page_size: int
) -> tuple[int, list[dict[str, Any]]]:
    return await _page(
        session,
        table="community_user_block",
        alias="block",
        columns=BLOCK_COLUMNS,
        joins=BLOCK_JOINS,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )


async def list_mutes(
    session: AsyncSession, *, user_id: int, page: int, page_size: int
) -> tuple[int, list[dict[str, Any]]]:
    return await _page(
        session,
        table="community_user_mute",
        alias="mute",
        columns=MUTE_COLUMNS,
        joins=MUTE_JOINS,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )


async def _target(session: AsyncSession, target_user_id: int) -> Any:
    rows = await fetch(
        session,
        'SELECT id, email FROM "user" WHERE id = :id',
        {"id": target_user_id},
    )
    if not rows:
        raise LookupError(target_user_id)
    return rows[0]


def _person(user: Any, profile: Any) -> dict[str, Any]:
    return {
        "id": user.id,
        "nickname": profile.nickname if profile else "",
        "avatar": profile.avatar if profile else "",
    }


async def follow_user(
    session: AsyncSession, *, follower_id: int, target_user_id: int
) -> tuple[dict[str, Any], bool]:
    target = await _target(session, target_user_id)
    if follower_id == target_user_id:
        raise PermissionError("community.cannot_follow_self")
    blocked = await fetch(
        session,
        "SELECT 1 FROM community_user_block"
        " WHERE (user_id = :a AND blocked_user_id = :b)"
        "    OR (user_id = :b AND blocked_user_id = :a)",
        {"a": follower_id, "b": target_user_id},
    )
    if blocked:
        raise PermissionError("community.cannot_follow_blocked_user")
    existing = await fetch(
        session,
        "SELECT created_at FROM community_user_follow WHERE follower_id = :a AND following_id = :b",
        {"a": follower_id, "b": target_user_id},
    )
    followed_at = existing[0].created_at if existing else None
    created = not existing
    if created:
        rows = await fetch(
            session,
            "INSERT INTO community_user_follow (follower_id, following_id,"
            " created_at) VALUES (:a, :b, now()) RETURNING created_at",
            {"a": follower_id, "b": target_user_id},
        )
        followed_at = rows[0].created_at
        profile = await fetch(
            session,
            "SELECT nickname, avatar FROM user_profile WHERE user_id = :id",
            {"id": target_user_id},
        )
        person = {
            "id": target_user_id,
            "nickname": profile[0].nickname if profile else "",
            "avatar": profile[0].avatar if profile else "",
        }
        activity = await fetch(
            session,
            """
            INSERT INTO community_activity (
                user_id, activity_type, target_user_id, message, visibility,
                feed_policy, group_key, dedupe_key, metadata, created_at
            ) VALUES (
                :user_id, 'user_followed', :target_id, 'Followed a user', 'public',
                'normal', :group_key, :dedupe_key, CAST(:metadata AS jsonb), now()
            )
            ON CONFLICT (dedupe_key) WHERE dedupe_key <> '' DO UPDATE SET
                message = EXCLUDED.message,
                metadata = EXCLUDED.metadata
            RETURNING id
            """,
            {
                "user_id": follower_id,
                "target_id": target_user_id,
                "group_key": f"follow:{follower_id}",
                "dedupe_key": f"user_followed:{follower_id}:{target_user_id}",
                "metadata": json.dumps({"target_user": person}),
            },
        )
        await fetch(
            session,
            """
            INSERT INTO community_notification (
                recipient_id, actor_id, notification_type, activity_id, metadata,
                created_at
            ) VALUES (
                :recipient, :actor, 'followed', :activity,
                CAST(:metadata AS jsonb), now()
            ) RETURNING id
            """,
            {
                "recipient": target_user_id,
                "actor": follower_id,
                "activity": activity[0].id,
                "metadata": json.dumps({"actor_id": follower_id}),
            },
        )
    profile = await fetch(
        session,
        "SELECT nickname, avatar FROM user_profile WHERE user_id = :id",
        {"id": target_user_id},
    )
    await session.commit()
    return {
        "user": _person(target, profile[0] if profile else None),
        "followed_at": _iso(followed_at),
    }, created


async def unfollow_user(session: AsyncSession, *, follower_id: int, target_user_id: int) -> None:
    await _target(session, target_user_id)
    await fetch(
        session,
        "DELETE FROM community_user_follow WHERE follower_id = :a"
        " AND following_id = :b RETURNING id",
        {"a": follower_id, "b": target_user_id},
    )
    await fetch(
        session,
        "DELETE FROM community_activity WHERE activity_type = 'user_followed'"
        " AND user_id = :a AND target_user_id = :b RETURNING id",
        {"a": follower_id, "b": target_user_id},
    )
    await session.commit()
