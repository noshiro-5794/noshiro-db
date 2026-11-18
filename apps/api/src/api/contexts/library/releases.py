"""The state a user gives to one release of a work they have in their library."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.fragments import fetch, isoformat

STATUSES = ("planned", "in_progress", "completed", "dropped")
REQUIRED = "This field is required."
NOT_CHOICE = '"{}" is not a valid choice.'
NOT_EARLIER = "Must not be earlier than started_at."


def _text(value: Any, limit: int) -> tuple[str, str | None]:
    if not isinstance(value, str):
        return "", "Not a valid string."
    if len(value) > limit:
        return "", f"Ensure this field has no more than {limit} characters."
    return value, None


def _date(value: Any) -> tuple[date | None, str | None]:
    if value is None:
        return None, None
    try:
        return date.fromisoformat(str(value)), None
    except ValueError:
        return None, "Date has wrong format. Use one of these formats instead: YYYY-MM-DD."


def validate(values: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[str]]]:
    columns: dict[str, Any] = {}
    errors: dict[str, list[str]] = {}
    status = values.get("status")
    if status is None:
        errors["status"] = [REQUIRED]
    elif status not in STATUSES:
        errors["status"] = [NOT_CHOICE.format(status)]
    else:
        columns["status"] = status
    for field, limit in (("language", 35), ("platform", 64), ("note", 2000)):
        if field in values:
            text, error = _text(values[field], limit)
            if error:
                errors[field] = [error]
            else:
                columns[field] = text
    for field in ("started_at", "completed_at"):
        if field in values:
            parsed, error = _date(values[field])
            if error:
                errors[field] = [error]
            else:
                columns[field] = parsed
    start = columns.get("started_at")
    end = columns.get("completed_at")
    if start and end and start > end:
        errors["completed_at"] = [NOT_EARLIER]
    return columns, errors


async def _release_for(session: AsyncSession, entry: Any, release_id: str) -> Any:
    root = await resolve(session, entry.entity_id) or entry.entity_id
    cluster = await cluster_ids(session, root)
    rows = await fetch(
        session,
        "SELECT release.entity_id FROM release"
        " JOIN release_work ON release_work.release_id = release.entity_id"
        " WHERE release.entity_id = CAST(:release_id AS uuid)"
        " AND release_work.work_id = ANY(CAST(:ids AS uuid[])) LIMIT 1",
        {"release_id": release_id, "ids": [str(value) for value in cluster]},
    )
    return rows[0] if rows else None


async def _entry(session: AsyncSession, user_id: int, entry_id: int) -> Any:
    rows = await fetch(
        session,
        "SELECT id, entity_id FROM user_library_entry WHERE id = :entry_id AND user_id = :user_id",
        {"entry_id": entry_id, "user_id": user_id},
    )
    if not rows:
        raise LookupError(entry_id)
    return rows[0]


async def put_state(
    session: AsyncSession,
    *,
    user_id: int,
    entry_id: int,
    release_id: str,
    values: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    entry = await _entry(session, user_id, entry_id)
    columns, errors = validate(values)
    if errors:
        raise ValueError(errors)
    found = await _release_for(session, entry, release_id)
    if found is None:
        raise FileNotFoundError(release_id)
    existing = await fetch(
        session,
        "SELECT id FROM user_release WHERE library_entry_id = :entry_id"
        " AND release_id = CAST(:release_id AS uuid)",
        {"entry_id": entry_id, "release_id": release_id},
    )
    if existing:
        assignments = ", ".join(f"{name} = :{name}" for name in columns)
        rows = await fetch(
            session,
            f"UPDATE user_release SET {assignments}, updated_at = now()"
            " WHERE id = :id RETURNING release_id, status, language, platform, note,"
            " started_at, completed_at, created_at, updated_at",
            {**columns, "id": existing[0].id},
        )
    else:
        rows = await fetch(
            session,
            "INSERT INTO user_release (library_entry_id, release_id, status,"
            " language, platform, note, started_at, completed_at, created_at,"
            " updated_at) VALUES (:entry_id, CAST(:release_id AS uuid), :status,"
            " :language, :platform, :note, :started_at, :completed_at, now(), now())"
            " RETURNING release_id, status, language, platform, note, started_at,"
            " completed_at, created_at, updated_at",
            {
                "entry_id": entry_id,
                "release_id": release_id,
                "language": columns.get("language", ""),
                "platform": columns.get("platform", ""),
                "note": columns.get("note", ""),
                "started_at": columns.get("started_at"),
                "completed_at": columns.get("completed_at"),
                **columns,
            },
        )
    await session.commit()
    row = rows[0]
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
    }, not existing


async def delete_state(
    session: AsyncSession, *, user_id: int, entry_id: int, release_id: str
) -> None:
    entry = await _entry(session, user_id, entry_id)
    rows = await fetch(
        session,
        "DELETE FROM user_release WHERE library_entry_id = :entry_id"
        " AND release_id = CAST(:release_id AS uuid) RETURNING id",
        {"entry_id": entry.id, "release_id": release_id},
    )
    if not rows:
        raise FileNotFoundError(release_id)
    await session.commit()
