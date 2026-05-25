from celery import shared_task

from apps.sync.services.incremental_sync_service import incremental_sync_service


@shared_task(
    bind=True,
    soft_time_limit=3600,
    time_limit=3900,
)
def run_incremental_sync_task(
    self,
    task_name: str | None = None,
    batch_size: int | None = None,
):
    if task_name:
        return incremental_sync_service.sync_task(
            task_name=task_name,
            batch_size=batch_size,
        )
    return incremental_sync_service.sync_all(
        batch_size=batch_size,
    )
