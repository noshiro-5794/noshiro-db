"""Blocking and muting another account.

Blocking is not a single row: it removes the follow relations in both directions
and the mute this user had set, because a block that leaves a follow behind is
not a block.
"""

from __future__ import annotations

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
