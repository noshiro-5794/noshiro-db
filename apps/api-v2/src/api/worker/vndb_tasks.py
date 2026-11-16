"""VNDB import task with committed leases and durable failure reporting."""

import asyncio
from typing import Any

from celery import current_task, shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.worker import jobs
from api.worker.providers.vndb import VNDBClient
from api.worker.runtime import run
from api.worker.session import session_scope
from api.worker.vndb_import import import_batch


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


async def import_work(
    vndb_id: str, *, include_related: bool, job_id: str | None, lease_owner: str
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
            current_label=f"Importing VNDB {vndb_id}",
            lease_owner=lease_owner,
        )
    try:
        if not vndb_id.startswith("v"):
            raise ValueError("VNDB work IDs must start with 'v'.")
        async with session_scope() as session:
            policy = await fetch(
                session, "SELECT storage_policy FROM provider WHERE slug='vndb'", {}
            )
        client = VNDBClient()
        client.forbid_storage(forbidden=bool(policy and policy[0].storage_policy == "forbidden"))
        try:
            batch = await asyncio.to_thread(
                client.fetch_import_batch, vndb_id, include_related=include_related
            )
        finally:
            client.close()
        async with session_scope() as session:
            if job_id and not await owns_job(session, job_id, lease_owner):
                return {"skipped": True, "reason": "job lease lost"}
            entity_id = await import_batch(session, vndb_id, batch)
            result = {"entity_id": str(entity_id), "provider": "vndb", "external_id": vndb_id}
            await jobs.advance(
                session,
                job_id=job_id,
                processed=1,
                synced=1,
                current_label=f"Imported VNDB {vndb_id}",
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


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.vndb.import_vndb_work_task",
    queue="sync",
    soft_time_limit=900,
    time_limit=960,
)
def import_vndb_work_task(
    vndb_id: str, *, include_related: bool = True, job_id: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = run(
        import_work(
            vndb_id,
            include_related=include_related,
            job_id=job_id,
            lease_owner=f"celery:{current_task.request.id}",
        )
    )
    return result
