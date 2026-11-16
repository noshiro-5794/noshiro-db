"""VNDB import task with committed leases and durable failure reporting."""

import asyncio
from typing import Any

from celery import current_task, shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from api.worker.importing import import_record
from api.worker.providers.vndb import VNDBClient, VNDBImportBatch
from api.worker.runtime import run
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
            return await asyncio.to_thread(
                client.fetch_import_batch, vndb_id, include_related=include_related
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
