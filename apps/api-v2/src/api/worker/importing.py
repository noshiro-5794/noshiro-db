"""Leased single-source imports with durable progress and cancellation checks."""

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.worker import jobs
from api.worker.session import session_scope


async def owns_job(session: AsyncSession, job_id: str, owner: str) -> bool:
    rows = await fetch(
        session,
        """
        SELECT id FROM sync_job WHERE id=:id AND status='running' AND lease_owner=:owner
          AND lease_expires_at>clock_timestamp() FOR UPDATE
        """,
        {"id": job_id, "owner": owner},
    )
    return bool(rows)


async def import_record[Payload](
    *,
    provider: str,
    label: str,
    external_id: str | int,
    job_id: str | None,
    lease_owner: str,
    fetch_payload: Callable[[bool], Awaitable[Payload]],
    project: Callable[[AsyncSession, Payload], Awaitable[Any]],
) -> dict[str, Any]:
    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=lease_owner, lease_seconds=960
        ):
            return {"skipped": True, "reason": "job already claimed"}
        await jobs.mark_running(
            session,
            job_id=job_id,
            total_count=1,
            current_label=f"Importing {label} {external_id}",
            lease_owner=lease_owner,
        )
    try:
        async with session_scope() as session:
            policy = await fetch(
                session,
                "SELECT storage_policy FROM provider WHERE slug=:provider",
                {"provider": provider},
            )
        payload = await fetch_payload(bool(policy and policy[0].storage_policy == "forbidden"))
        async with session_scope() as session:
            if job_id and not await owns_job(session, job_id, lease_owner):
                return {"skipped": True, "reason": "job lease lost"}
            entity_id = await project(session, payload)
            result = {"entity_id": str(entity_id), "provider": provider, "external_id": external_id}
            await jobs.advance(
                session,
                job_id=job_id,
                processed=1,
                synced=1,
                current_label=f"Imported {label} {external_id}",
                lease_owner=lease_owner,
            )
            await jobs.mark_succeeded(
                session, job_id=job_id, result=result, lease_owner=lease_owner
            )
            return result
    except Exception as error:
        async with session_scope() as session:
            if job_id and await owns_job(session, job_id, lease_owner):
                await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
        raise
