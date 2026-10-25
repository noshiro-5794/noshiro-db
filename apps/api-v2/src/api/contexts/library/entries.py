"""A user's library entries, with the entity summary each one points at."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

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


STATUSES = ("doing", "wish", "done", "on_hold", "dropped")
NOT_CHOICE = '"{}" is not a valid choice.'


def _integer(value: Any, low: int, high: int) -> tuple[int | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, bool) or not isinstance(value, int):
        return None, "A valid integer is required."
    if value < low:
        return None, f"Ensure this value is greater than or equal to {low}."
    if value > high:
        return None, f"Ensure this value is less than or equal to {high}."
    return value, None


def _decimal(value: Any) -> tuple[float | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, "A valid number is required."
    try:
        number = round(float(value), 1)
    except (TypeError, ValueError):
        return None, "A valid number is required."
    if number < 0:
        return None, "Ensure this value is greater than or equal to 0."
    if number > 10:
        return None, "Ensure this value is less than or equal to 10."
    return number, None


def _date(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "Date has wrong format."
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, "Date has wrong format. Use one of these formats instead: YYYY-MM-DD."


def validate(values: dict[str, Any], current: Any) -> tuple[dict[str, Any], dict[str, list[str]]]:
    columns: dict[str, Any] = {}
    errors: dict[str, list[str]] = {}
    if "status" in values:
        if values["status"] not in STATUSES:
            errors["status"] = [NOT_CHOICE.format(values["status"])]
        else:
            columns["status"] = values["status"]
    if "simple_rating" in values:
        number, error = _integer(values["simple_rating"], 1, 5)
        (
            errors.setdefault("simple_rating", [error])
            if error
            else columns.update(simple_rating=number)
        )
    if "rating" in values:
        amount, error = _decimal(values["rating"])
        if error:
            errors["rating"] = [error]
        else:
            columns["rating"] = amount
    if "comment" in values:
        comment = values["comment"]
        if not isinstance(comment, str):
            errors["comment"] = ["Not a valid string."]
        elif len(comment) > 2000:
            errors["comment"] = ["Ensure this field has no more than 2000 characters."]
        else:
            columns["comment"] = comment
    if "is_public" in values:
        flag = values["is_public"]
        if not isinstance(flag, bool):
            errors["is_public"] = ["Must be a valid boolean."]
        else:
            columns["is_public"] = flag
    for field in ("watch_start_date", "watch_end_date"):
        if field in values:
            parsed, error = _date(values[field])
            if error:
                errors[field] = [error]
            else:
                columns[field] = parsed
    start = columns.get("watch_start_date", current.watch_start_date)
    end = columns.get("watch_end_date", current.watch_end_date)
    if start and end and start > end:
        errors["watch_end_date"] = ["Must not be earlier than watch_start_date."]
    return columns, errors


async def patch_entry(
    session: AsyncSession, *, user_id: int, entry_id: int, values: dict[str, Any]
) -> dict[str, Any]:
    rows = await fetch(
        session,
        f"SELECT {ENTRY_COLUMNS} FROM user_library_entry AS entry"
        " WHERE entry.id = :entry_id AND entry.user_id = :user_id",
        {"entry_id": entry_id, "user_id": user_id},
    )
    if not rows:
        raise LookupError(entry_id)
    columns, errors = validate(values, rows[0])
    if errors:
        raise ValueError(errors)
    if columns:
        assignments = ", ".join(f"{name} = :{name}" for name in columns)
        await fetch(
            session,
            f"UPDATE user_library_entry SET {assignments}, updated_at = now()"
            " WHERE id = :entry_id AND user_id = :user_id RETURNING id",
            {**columns, "entry_id": entry_id, "user_id": user_id},
        )
        await session.commit()
    return await get_entry(session, user_id=user_id, entry_id=entry_id)


REQUIRED = "entity_id and status are required."
NOT_A_WORK = "A current Work entity is required."


async def create_entry(
    session: AsyncSession, *, user_id: int, values: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    raw_id = values.pop("entity_id", None)
    if raw_id is None or "status" not in values:
        raise ValueError({"entity_id": REQUIRED})
    columns, errors = validate(values, _Blank())
    if errors:
        raise ValueError(errors)
    try:
        wanted = UUID(str(raw_id))
    except ValueError as error:
        raise ValueError({"entity_id": NOT_A_WORK}) from error
    rows = await fetch(
        session,
        "SELECT id, kind, lifecycle FROM entity WHERE id = CAST(:id AS uuid)",
        {"id": str(wanted)},
    )
    if not rows:
        raise ValueError({"entity_id": NOT_A_WORK})
    root = await resolve(session, wanted) or wanted
    resolved = [row for row in rows if row.id == root]
    if not resolved or resolved[0].kind != "work" or resolved[0].lifecycle != "active":
        raise ValueError({"entity_id": NOT_A_WORK})
    cluster = await cluster_ids(session, root)
    existing = await fetch(
        session,
        f"SELECT {ENTRY_COLUMNS} FROM user_library_entry AS entry"
        " WHERE entry.user_id = :user_id"
        " AND entry.entity_id = ANY(CAST(:ids AS uuid[]))"
        " ORDER BY entry.id LIMIT 1 FOR UPDATE",
        {"user_id": user_id, "ids": [str(value) for value in cluster]},
    )
    if existing:
        assignments = ", ".join(f"{name} = :{name}" for name in columns)
        if assignments:
            await fetch(
                session,
                f"UPDATE user_library_entry SET {assignments}, updated_at = now()"
                " WHERE id = :entry_id RETURNING id",
                {**columns, "entry_id": existing[0].id},
            )
        await session.commit()
        return await get_entry(session, user_id=user_id, entry_id=existing[0].id), False
    fields = {"user_id": user_id, "entity_id": root, **columns}
    names = ", ".join(fields)
    placeholders = ", ".join(f":{name}" for name in fields)
    inserted = await fetch(
        session,
        f"INSERT INTO user_library_entry ({names}, created_at, updated_at)"
        f" VALUES ({placeholders}, now(), now()) RETURNING id",
        fields,
    )
    await session.commit()
    return await get_entry(session, user_id=user_id, entry_id=inserted[0].id), True


class _Blank:
    """The patch validator reads the current row for the date pair; a new entry has none."""

    watch_start_date = None
    watch_end_date = None


TAG_IDS_OR_NAMES = "tag_ids or tag_names is required."
UNKNOWN_TAG = "Contains an unknown tag."
BLANK_TAG = "Tag name can not be blank."


async def entry_tags(session: AsyncSession, *, user_id: int, entry_id: int) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        "SELECT tag.id, tag.name FROM user_library_entry_tag AS relation"
        " JOIN user_tag AS tag ON tag.id = relation.tag_id"
        " JOIN user_library_entry AS entry ON entry.id = relation.user_subject_id"
        " WHERE entry.id = :entry_id AND entry.user_id = :user_id"
        " ORDER BY tag.name, tag.id",
        {"entry_id": entry_id, "user_id": user_id},
    )
    return [{"id": row.id, "name": row.name} for row in rows]


async def replace_tags(
    session: AsyncSession, *, user_id: int, entry_id: int, body: dict[str, Any]
) -> list[dict[str, Any]]:
    if "tag_ids" not in body and "tag_names" not in body:
        raise ValueError({"non_field_errors": [TAG_IDS_OR_NAMES]})
    existing = await fetch(
        session,
        "SELECT id FROM user_library_entry WHERE id = :entry_id AND user_id = :user_id",
        {"entry_id": entry_id, "user_id": user_id},
    )
    if not existing:
        raise LookupError(entry_id)
    tag_ids = list(dict.fromkeys(body.get("tag_ids") or []))
    tags = []
    if tag_ids:
        rows = await fetch(
            session,
            "SELECT id, name FROM user_tag WHERE user_id = :user_id"
            " AND id = ANY(CAST(:ids AS bigint[])) ORDER BY name, id",
            {"user_id": user_id, "ids": tag_ids},
        )
        if {row.id for row in rows} != set(tag_ids):
            raise ValueError({"tag_ids": UNKNOWN_TAG})
        tags = [{"id": row.id, "name": row.name} for row in rows]
    for raw in body.get("tag_names") or []:
        name = str(raw).strip()
        if not name:
            raise ValueError({"tag_names": [BLANK_TAG]})
        if len(name) > 64:
            raise ValueError({"tag_names": ["Ensure this field has no more than 64 characters."]})
        rows = await fetch(
            session,
            "INSERT INTO user_tag (user_id, name) VALUES (:user_id, :name)"
            " ON CONFLICT (user_id, name) DO NOTHING RETURNING id",
            {"user_id": user_id, "name": name},
        )
        if not rows:
            rows = await fetch(
                session,
                "SELECT id, name FROM user_tag WHERE user_id = :user_id AND name = :name",
                {"user_id": user_id, "name": name},
            )
        if all(tag["id"] != rows[0].id for tag in tags):
            tags.append({"id": rows[0].id, "name": rows[0].name})
    await fetch(
        session,
        "DELETE FROM user_library_entry_tag WHERE user_subject_id = :entry_id RETURNING id",
        {"entry_id": entry_id},
    )
    for tag in tags:
        await fetch(
            session,
            "INSERT INTO user_library_entry_tag (user_subject_id, tag_id)"
            " VALUES (:entry_id, :tag_id) RETURNING id",
            {"entry_id": entry_id, "tag_id": tag["id"]},
        )
    await session.commit()
    return tags
