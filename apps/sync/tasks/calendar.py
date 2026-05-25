from celery import shared_task

from apps.sync.services.calendar_service import calendar_sync_service


@shared_task(
    bind=True,
    soft_time_limit=3600,
    time_limit=3900,
)
def sync_calendar_task(self, sync_subject_details: bool = True):
    return calendar_sync_service.sync_calendar(
        sync_subject_details=sync_subject_details,
    )
