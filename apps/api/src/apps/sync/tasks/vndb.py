from datetime import date

from celery import current_task, shared_task
from django.utils import timezone

from apps.sync.providers.vndb import VNDB_SOURCE
from apps.sync.services.campaign import sync_campaign_service
from apps.sync.services.sync_job import sync_job_service
from apps.sync.services.vndb import vndb_import_service
from apps.sync.tasks.campaign import run_sync_campaign_task


@shared_task(soft_time_limit=300, time_limit=360)
def run_vndb_incremental_task(job_id: str | None = None) -> dict:
    """Start today's pass over the works VNDB added since the last watermark.

    VNDB had no schedule at all: its delta re-fetched every record already
    held, which is not an increment, so nothing here kept up with new releases.
    A daily campaign walks the ids above the watermark instead, and the
    campaign machinery carries it to completion across its own steps.
    """
    lease_owner = f"celery:{current_task.request.id}"
    if job_id and not sync_job_service.claim(
        job_id=job_id,
        lease_owner=lease_owner,
        lease_seconds=360,
    ):
        return {"skipped": True, "reason": "job already claimed"}
    campaign = sync_campaign_service.create_campaign(
        provider_slug=VNDB_SOURCE.slug,
        campaign_type="incremental",
        # One pass a day: the key makes a retry of the same day a no-op rather
        # than a second sweep of the same ids.
        idempotency_key=f"vndb-incremental-{date.today().isoformat()}",
        parameters={"fetch_batch_size": 50, "step_delay_seconds": 1},
    )
    sync_job_service.mark_running(
        job_id=job_id,
        total_count=1,
        current_label=f"VNDB incremental campaign {campaign.pk}",
        lease_owner=lease_owner,
    )
    result = run_sync_campaign_task.delay(str(campaign.pk))
    response = {
        "campaign_id": str(campaign.pk),
        "task_id": getattr(result, "id", ""),
        "requested_at": timezone.now().isoformat(),
    }
    sync_job_service.mark_succeeded(
        job_id=job_id,
        result=response,
        current_label="VNDB incremental campaign started",
        lease_owner=lease_owner,
    )
    return response


@shared_task(soft_time_limit=900, time_limit=960)
def import_vndb_work_task(
    vndb_id: str,
    *,
    include_related: bool = True,
    job_id: str | None = None,
) -> dict:
    lease_owner = f"celery:{current_task.request.id}"
    if job_id and not sync_job_service.claim(
        job_id=job_id,
        lease_owner=lease_owner,
        lease_seconds=960,
    ):
        return {"skipped": True, "reason": "job already claimed"}
    sync_job_service.mark_running(
        job_id=job_id,
        total_count=1,
        current_label=f"Importing VNDB {vndb_id}",
        lease_owner=lease_owner,
    )
    try:
        entity = vndb_import_service.import_work(
            vndb_id=vndb_id,
            include_related=include_related,
        )
        result = {
            "entity_id": str(entity.id),
            "provider": "vndb",
            "external_id": vndb_id,
        }
        sync_job_service.advance(
            job_id=job_id,
            processed=1,
            synced=1,
            current_label=f"Imported VNDB {vndb_id}",
            lease_owner=lease_owner,
        )
        sync_job_service.mark_succeeded(
            job_id=job_id,
            result=result,
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
