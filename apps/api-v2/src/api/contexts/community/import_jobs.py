"""An import job as staff see it: its parameters, result and progress."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch, isoformat
from api.shared.cursor import Cursor, position_of

QUERY = """
    SELECT id, job_type, parameters, result, error, status, current_label,
           total_count, processed_count, synced_count, skipped_count, failed_count,
           created_at, started_at, finished_at, updated_at
    FROM sync_job WHERE id = CAST(:id AS uuid)
"""


PROVIDERS = {"vndb_import": "vndb", "anilist_import": "anilist"}


def _provider(job_type: str | None) -> str | None:
    """None when no import provider is registered for the job type."""
    return PROVIDERS.get(job_type or "")


def _params(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


async def import_job(session: AsyncSession, *, job_id: str) -> dict[str, Any]:
    rows = await fetch(session, QUERY, {"id": job_id})
    if not rows:
        raise LookupError(job_id)
    row = rows[0]
    provider = _provider(row.job_type)
    if provider is None:
        raise KeyError(row.job_type)
    parameters = _params(row.parameters)
    return {
        "id": str(row.id),
        "provider": provider,
        "external_id": parameters.get("external_id"),
        "status": row.status,
        "parameters": parameters,
        "result": row.result,
        "error": row.error or None,
        "progress": {
            "current_label": row.current_label,
            "total": row.total_count,
            "processed": row.processed_count,
            "synced": row.synced_count,
            "skipped": row.skipped_count,
            "failed": row.failed_count,
        },
        "created_at": isoformat(row.created_at),
        "started_at": isoformat(row.started_at),
        "finished_at": isoformat(row.finished_at),
        "updated_at": isoformat(row.updated_at),
    }


JOB_TYPES = {"vndb": "vndb_import", "anilist": "anilist_import"}


async def list_import_jobs(
    session: AsyncSession,
    *,
    viewer_id: int,
    provider: str,
    status: str,
    cursor: Cursor,
    page_size: int,
) -> tuple[list[dict[str, Any]], Cursor | None]:
    job_type = JOB_TYPES.get(provider or "vndb")
    if job_type is None:
        raise ValueError({"provider": [f'"{provider}" is not a valid choice.']})
    clauses = ["job_type = :job_type"]
    params: dict[str, Any] = {"job_type": job_type, "limit": page_size + 1, "offset": cursor.offset}
    if status:
        clauses.append("status = :status")
        params["status"] = status
    if cursor.position is not None:
        clauses.append("created_at < CAST(:position AS timestamptz)")
        params["position"] = cursor.position
    rows = await fetch(
        session,
        "SELECT id, job_type, parameters, result, error, status, current_label,"
        " total_count, processed_count, synced_count, skipped_count, failed_count,"
        " created_at, started_at, finished_at, updated_at FROM sync_job"
        " WHERE "
        + " AND ".join(clauses)
        + " ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :offset",
        params,
    )
    page = rows[:page_size]
    extra = rows[page_size] if len(rows) > page_size else None
    next_cursor = (
        Cursor(offset=0, reverse=False, position=position_of(page[-1]))
        if extra is not None and page
        else None
    )
    return [_job(row) for row in page], next_cursor


def _job(row: Any) -> dict[str, Any]:
    parameters = _params(row.parameters)
    return {
        "id": str(row.id),
        "provider": _provider(row.job_type) or "unknown",
        "external_id": parameters.get("external_id"),
        "status": row.status,
        "parameters": parameters,
        "result": row.result,
        "error": row.error or None,
        "progress": {
            "current_label": row.current_label,
            "total": row.total_count,
            "processed": row.processed_count,
            "synced": row.synced_count,
            "skipped": row.skipped_count,
            "failed": row.failed_count,
        },
        "created_at": isoformat(row.created_at),
        "started_at": isoformat(row.started_at),
        "finished_at": isoformat(row.finished_at),
        "updated_at": isoformat(row.updated_at),
    }
