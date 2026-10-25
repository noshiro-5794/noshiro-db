"""An import job as staff see it: its parameters, result and progress."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch, isoformat

QUERY = """
    SELECT id, job_type, parameters, result, error, status, current_label,
           total_count, processed_count, synced_count, skipped_count, failed_count,
           created_at, started_at, finished_at, updated_at
    FROM sync_job WHERE id = CAST(:id AS uuid)
"""


def _provider(job_type: str | None) -> str:
    if not job_type:
        return "unknown"
    return job_type.replace("_import", "")


def _params(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


async def import_job(session: AsyncSession, *, job_id: str) -> dict[str, Any]:
    rows = await fetch(session, QUERY, {"id": job_id})
    if not rows:
        raise LookupError(job_id)
    row = rows[0]
    parameters = _params(row.parameters)
    return {
        "id": str(row.id),
        "provider": _provider(row.job_type),
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
