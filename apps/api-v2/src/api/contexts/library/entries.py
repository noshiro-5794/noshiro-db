"""A user's library entries, with the entity summary each one points at."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.fragments import fetch, isoformat
from api.contexts.presentation.summary import entity_summary

ORDERINGS = frozenset({"created_at", "-created_at", "updated_at", "-updated_at"})

ENTRY_COLUMNS = """
    entry.id, entry.status, entry.simple_rating, entry.rating, entry.comment,
    entry.watch_start_date, entry.watch_end_date, entry.is_public,
    entry.created_at, entry.updated_at, entry.entity_id
"""


def _release(row: Any) -> dict[str, Any]:
    return {
        "release_id": str(row.release_id),
        "status": row.status,
        "language": row.language,
        "platform": row.platform,
        "note": row.note,
        "started_at": isoformat(row.started_at),
        "completed_at": isoformat(row.completed_at),
        "created_at": isoformat(row.created_at),
        "updated_at": isoformat(row.updated_at),
    }


async def _releases(session: AsyncSession, entry_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not entry_ids:
        return {}
    rows = await fetch(
        session,
        "SELECT library_entry_id, release_id, status, language, platform, note,"
        " started_at, completed_at, created_at, updated_at"
        " FROM user_release WHERE library_entry_id = ANY(CAST(:ids AS bigint[]))"
        " ORDER BY id",
        {"ids": entry_ids},
    )
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.library_entry_id, []).append(_release(row))
    return grouped


async def list_entries(
    session: AsyncSession,
    *,
    user_id: int,
    status: str,
    subject_type: str,
    keyword: str,
    tag_id: int,
    ordering: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    clauses = ["entry.user_id = :user_id"]
    params: dict[str, Any] = {}
    if status:
        clauses.append("entry.status = :status")
        params["status"] = status
    if subject_type:
        clauses.append(
            "EXISTS (SELECT 1 FROM work WHERE work.entity_id = entry.entity_id"
            " AND work.work_type = :subject_type)"
        )
        params["subject_type"] = subject_type
    if keyword:
        clauses.append(
            "(EXISTS (SELECT 1 FROM entity_name AS name"
            " WHERE name.entity_id = entry.entity_id"
            " AND name.text ILIKE :keyword)"
            " OR entry.comment ILIKE :keyword)"
        )
        params["keyword"] = f"%{keyword}%"
    if tag_id:
        clauses.append(
            "EXISTS (SELECT 1 FROM user_library_entry_tag AS relation"
            " JOIN user_tag AS tag ON tag.id = relation.tag_id"
            " WHERE relation.user_subject_id = entry.id"
            " AND relation.tag_id = :tag_id AND tag.user_id = :user_id)"
        )
        params["tag_id"] = tag_id
    where = " AND ".join(clauses)
    field = ordering.lstrip("-")
    direction = "DESC" if ordering.startswith("-") else "ASC"
    if field not in {"created_at", "updated_at"}:
        field, direction = "updated_at", "DESC"
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM user_library_entry AS entry WHERE {where}",
        {**params, "user_id": user_id},
    )
    rows = await fetch(
        session,
        f"SELECT {ENTRY_COLUMNS} FROM user_library_entry AS entry WHERE {where}"
        f" ORDER BY entry.{field} {direction}, entry.id DESC"
        " LIMIT :limit OFFSET :offset",
        {
            **params,
            "user_id": user_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    releases = await _releases(session, [row.id for row in rows])
    results = [await entry_data(session, row, releases.get(row.id, [])) for row in rows]
    return int(total[0].total), results


async def entry_data(
    session: AsyncSession, row: Any, releases: list[dict[str, Any]]
) -> dict[str, Any]:
    root = await resolve(session, row.entity_id)
    cluster = await cluster_ids(session, root) if root is not None else {row.entity_id}
    summary = await entity_summary(
        session,
        root=root or row.entity_id,
        cluster_ids=[str(value) for value in cluster],
        language="",
    )
    return {
        "id": row.id,
        "entity": summary,
        "status": row.status,
        "simple_rating": row.simple_rating,
        "rating": float(row.rating) if row.rating is not None else None,
        "comment": row.comment,
        "watch_start_date": isoformat(row.watch_start_date),
        "watch_end_date": isoformat(row.watch_end_date),
        "is_public": row.is_public,
        "releases": releases,
        "created_at": isoformat(row.created_at),
        "updated_at": isoformat(row.updated_at),
    }


async def get_entry(session: AsyncSession, *, user_id: int, entry_id: int) -> dict[str, Any]:
    rows = await fetch(
        session,
        f"SELECT {ENTRY_COLUMNS} FROM user_library_entry AS entry"
        " WHERE entry.id = :entry_id AND entry.user_id = :user_id",
        {"entry_id": entry_id, "user_id": user_id},
    )
    if not rows:
        raise LookupError(entry_id)
    releases = await _releases(session, [entry_id])
    return await entry_data(session, rows[0], releases.get(entry_id, []))


async def delete_entry(session: AsyncSession, *, user_id: int, entry_id: int) -> None:
    rows = await fetch(
        session,
        "DELETE FROM user_library_entry WHERE id = :entry_id AND user_id = :user_id RETURNING id",
        {"entry_id": entry_id, "user_id": user_id},
    )
    if not rows:
        raise LookupError(entry_id)
    await session.commit()
