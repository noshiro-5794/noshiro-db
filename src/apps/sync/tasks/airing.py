from celery import current_task, shared_task

from apps.sync.services.airing_daily_sync_service import airing_daily_sync_service
from apps.sync.services.sync_job_service import sync_job_service


@shared_task(
    soft_time_limit=1800,
    time_limit=2100,
)
def run_airing_daily_task(
    batch_size: int | None = None,
    job_id: str | None = None,
):
    lease_owner = f"celery:{current_task.request.id}"
    if job_id and not sync_job_service.claim(
        job_id=job_id,
        lease_owner=lease_owner,
        lease_seconds=2100,
    ):
        return {"skipped": True, "reason": "job already claimed"}
    try:
        result = airing_daily_sync_service.sync_day(
            batch_size=batch_size,
            job_id=job_id,
        )
        sync_job_service.mark_succeeded(
            job_id=job_id,
            result=result,
            current_label="Airing daily task completed",
            lease_owner=lease_owner,
        )
        return result
    except Exception as exc:
        sync_job_service.mark_failed(
            job_id=job_id,
            error=exc,
            lease_owner=lease_owner,
        )
        raise
