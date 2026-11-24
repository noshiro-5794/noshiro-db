"""VNDB import task with committed leases and durable failure reporting."""

from datetime import UTC, date, datetime
from typing import Any

from celery import current_task, shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.synchronization import campaigns
from api.integrations.providers.vndb import VNDBClient, VNDBImportBatch
from api.shared import dispatch
from api.worker import jobs
from api.worker.importing import import_record
from api.worker.runtime import run
from api.worker.session import session_scope
from api.worker.source_fetches import fetch_archived
from api.worker.vndb_import import import_batch


async def import_work(
    vndb_id: str, *, include_related: bool, job_id: str | None, lease_owner: str
) -> dict[str, Any]:
    async def fetch_payload(forbidden: bool) -> VNDBImportBatch:
        if not vndb_id.startswith("v"):
            raise ValueError("VNDB work IDs must start with 'v'.")
        client = VNDBClient()
        client.forbid_storage(forbidden=forbidden)
        try:
            return await fetch_archived(
                session_scope, client.fetch_import_batch, vndb_id, include_related=include_related
            )
        finally:
            client.close()

    async def project(session: AsyncSession, batch: VNDBImportBatch) -> Any:
        return await import_batch(session, vndb_id, batch)

    return await import_record(
        provider="vndb",
        label="VNDB",
        external_id=vndb_id,
        job_id=job_id,
        lease_owner=lease_owner,
        fetch_payload=fetch_payload,
        project=project,
    )


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


async def start_incremental(job_id: str | None, lease_owner: str) -> dict[str, Any]:
    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=lease_owner, lease_seconds=360
        ):
            return {"skipped": True, "reason": "job already claimed"}
    try:
        requested = datetime.now(UTC)
        async with session_scope() as session:
            identifier = await campaigns.create_campaign(
                session,
                provider="vndb",
                campaign_type="incremental",
                idempotency_key=f"vndb-incremental-{date.today().isoformat()}",
                parameters={"fetch_batch_size": 50, "step_delay_seconds": 1},
            )
            await jobs.mark_running(
                session,
                job_id=job_id,
                total_count=1,
                current_label=f"VNDB incremental campaign {identifier}",
                lease_owner=lease_owner,
            )
        task_id = await dispatch.enqueue(dispatch.SYNC_TASK, {"campaign_id": str(identifier)})
        response = {
            "campaign_id": str(identifier),
            "task_id": task_id,
            "requested_at": requested.isoformat(),
        }
        async with session_scope() as session:
            await jobs.mark_succeeded(
                session,
                job_id=job_id,
                result=response,
                current_label="VNDB incremental campaign started",
                lease_owner=lease_owner,
            )
        return response
    except Exception as error:
        async with session_scope() as session:
            await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
        raise


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.vndb.run_vndb_incremental_task",
    queue="sync",
    soft_time_limit=300,
    time_limit=360,
)
def run_vndb_incremental_task(job_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = run(start_incremental(job_id, f"celery:{current_task.request.id}"))
    return result
