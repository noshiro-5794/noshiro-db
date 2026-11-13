"""The job row lifecycle, ported from `apps/sync/services/sync_job.py`.

Every moved task reports progress through these functions, so they are the first thing
that has to exist on the replacement side. The semantics are kept exactly: the same
conditional updates, the same lease rules, and the same "only a queued or running job may
be touched" guards, because the API reads these rows back to the user.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

DEFAULT_LEASE_SECONDS = 3600
OPEN_STATUSES = ("queued", "running")


def _now() -> datetime:
    return datetime.now(UTC)


async def create_job(
    session: AsyncSession, *, job_type: str, parameters: dict[str, Any] | None = None
) -> Any:
    rows = await fetch(
        session,
        "INSERT INTO sync_job (job_type, status, parameters, created_at, updated_at)"
        " VALUES (:job_type, 'queued', CAST(:parameters AS jsonb), now(), now())"
        " RETURNING id",
        {"job_type": job_type, "parameters": __import__("json").dumps(parameters or {})},
    )
    return rows[0].id


async def bind_celery_task(session: AsyncSession, *, job_id: Any, celery_task_id: str) -> None:
    await fetch(
        session,
        "UPDATE sync_job SET celery_task_id = :task, updated_at = now()"
        " WHERE id = :id RETURNING id",
        {"task": celery_task_id, "id": job_id},
    )


async def mark_running(
    session: AsyncSession,
    *,
    job_id: Any,
    total_count: int | None = None,
    current_label: str = "",
    lease_owner: str | None = None,
) -> None:
    if job_id is None:
        return
    await fetch(
        session,
        "UPDATE sync_job SET status = 'running',"
        " started_at = COALESCE(started_at, now()), current_label = :label,"
        " total_count = COALESCE(:total, total_count), updated_at = now()"
        " WHERE id = :id AND status = ANY(:open)"
        " AND (:owner IS NULL OR lease_owner = :owner) RETURNING id",
        {
            "label": current_label,
            "total": None if total_count is None else max(0, int(total_count)),
            "id": job_id,
            "open": list(OPEN_STATUSES),
            "owner": lease_owner,
        },
    )


async def set_total(
    session: AsyncSession, *, job_id: Any, total_count: int, current_label: str = ""
) -> None:
    if job_id is None:
        return
    await fetch(
        session,
        "UPDATE sync_job SET total_count = :total, updated_at = now(),"
        " current_label = CASE WHEN :label = '' THEN current_label ELSE :label END"
        " WHERE id = :id AND status = 'running' RETURNING id",
        {"total": max(0, int(total_count)), "label": current_label, "id": job_id},
    )


async def advance(
    session: AsyncSession,
    *,
    job_id: Any,
    processed: int = 1,
    synced: int = 0,
    skipped: int = 0,
    failed: int = 0,
    current_label: str = "",
    lease_owner: str | None = None,
) -> None:
    if job_id is None:
        return
    await fetch(
        session,
        "UPDATE sync_job SET processed_count = processed_count + :processed,"
        " synced_count = synced_count + :synced,"
        " skipped_count = skipped_count + :skipped,"
        " failed_count = failed_count + :failed,"
        " current_label = CASE WHEN :label = '' THEN current_label ELSE :label END,"
        " updated_at = now()"
        " WHERE id = :id AND status = 'running'"
        " AND (:owner IS NULL OR lease_owner = :owner) RETURNING id",
        {
            "processed": max(0, int(processed)),
            "synced": max(0, int(synced)),
            "skipped": max(0, int(skipped)),
            "failed": max(0, int(failed)),
            "label": current_label,
            "id": job_id,
            "owner": lease_owner,
        },
    )


async def mark_succeeded(
    session: AsyncSession,
    *,
    job_id: Any,
    result: dict[str, Any] | None = None,
    current_label: str = "Completed",
    lease_owner: str | None = None,
) -> None:
    if job_id is None:
        return
    await fetch(
        session,
        "UPDATE sync_job SET status = 'succeeded', result = CAST(:result AS jsonb),"
        " current_label = :label, finished_at = now(), updated_at = now()"
        " WHERE id = :id AND status = ANY(:open)"
        " AND (:owner IS NULL OR lease_owner = :owner) RETURNING id",
        {
            "result": __import__("json").dumps(result or {}),
            "label": current_label,
            "id": job_id,
            "open": list(OPEN_STATUSES),
            "owner": lease_owner,
        },
    )


async def mark_failed(
    session: AsyncSession,
    *,
    job_id: Any,
    error: Exception | str,
    current_label: str = "Failed",
    lease_owner: str | None = None,
) -> None:
    if job_id is None:
        return
    await fetch(
        session,
        "UPDATE sync_job SET status = 'failed', error = :error,"
        " current_label = :label, finished_at = now(), updated_at = now()"
        " WHERE id = :id AND status <> 'succeeded'"
        " AND (:owner IS NULL OR lease_owner = :owner) RETURNING id",
        {
            "error": str(error)[:4000],
            "label": current_label,
            "id": job_id,
            "owner": lease_owner,
        },
    )


async def claim(
    session: AsyncSession,
    *,
    job_id: Any,
    lease_owner: str,
    lease_seconds: int | None = None,
) -> bool:
    if job_id is None:
        return False
    now = _now()
    expires = now + timedelta(seconds=max(30, int(lease_seconds or DEFAULT_LEASE_SECONDS)))
    rows = await fetch(
        session,
        "UPDATE sync_job SET status = 'running',"
        " started_at = COALESCE(started_at, now()), heartbeat_at = now(),"
        " lease_owner = :owner, lease_expires_at = :expires,"
        " attempt = attempt + 1, updated_at = now()"
        " WHERE id = :id AND status = ANY(:open)"
        " AND (lease_owner = :owner OR lease_expires_at IS NULL"
        "      OR lease_expires_at <= :now)"
        " RETURNING id",
        {
            "owner": lease_owner,
            "expires": expires,
            "id": job_id,
            "open": list(OPEN_STATUSES),
            "now": now,
        },
    )
    return bool(rows)


async def heartbeat(
    session: AsyncSession, *, job_id: Any, lease_owner: str, lease_seconds: int | None = None
) -> bool:
    if job_id is None:
        return False
    now = _now()
    expires = now + timedelta(seconds=max(30, int(lease_seconds or DEFAULT_LEASE_SECONDS)))
    rows = await fetch(
        session,
        "UPDATE sync_job SET heartbeat_at = :now, lease_expires_at = :expires,"
        " updated_at = now()"
        " WHERE id = :id AND status = 'running' AND lease_owner = :owner"
        " RETURNING id",
        {"now": now, "expires": expires, "id": job_id, "owner": lease_owner},
    )
    return bool(rows)


async def release(session: AsyncSession, *, job_id: Any, lease_owner: str) -> None:
    if job_id is None:
        return
    await fetch(
        session,
        "UPDATE sync_job SET lease_expires_at = :now, updated_at = now()"
        " WHERE id = :id AND status = 'running' AND lease_owner = :owner RETURNING id",
        {"now": _now(), "id": job_id, "owner": lease_owner},
    )


async def stale_running_jobs(session: AsyncSession, *, before: Any | None = None) -> list[Any]:
    return await fetch(
        session,
        "SELECT id, lease_owner, attempt, celery_task_id FROM sync_job"
        " WHERE status = 'running' AND lease_expires_at < :before"
        " ORDER BY lease_expires_at",
        {"before": before or _now()},
    )
