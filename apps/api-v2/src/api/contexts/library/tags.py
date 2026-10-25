"""A user's own tag names, used to label library entries later."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


async def list_tags(
    session: AsyncSession, *, user_id: int, page: int, page_size: int
) -> tuple[int, list[dict[str, Any]]]:
    total = await fetch(
        session,
        "SELECT count(*) AS total FROM user_tag WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    rows = await fetch(
        session,
        "SELECT id, name FROM user_tag WHERE user_id = :user_id"
        " ORDER BY name, id LIMIT :limit OFFSET :offset",
        {"user_id": user_id, "limit": page_size, "offset": (page - 1) * page_size},
    )
    return int(total[0].total), [{"id": row.id, "name": row.name} for row in rows]


async def create_tag(
    session: AsyncSession, *, user_id: int, name: str
) -> tuple[dict[str, Any], bool]:
    rows = await fetch(
        session,
        "INSERT INTO user_tag (user_id, name) VALUES (:user_id, :name)"
        " ON CONFLICT (user_id, name) DO NOTHING RETURNING id, name",
        {"user_id": user_id, "name": name},
    )
    created = bool(rows)
    if not rows:
        rows = await fetch(
            session,
            "SELECT id, name FROM user_tag WHERE user_id = :user_id AND name = :name",
            {"user_id": user_id, "name": name},
        )
    await session.commit()
    return {"id": rows[0].id, "name": rows[0].name}, created
