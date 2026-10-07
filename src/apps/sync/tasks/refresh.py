from celery import shared_task
from django.conf import settings

from apps.sync.services.subject_refresh_service import subject_refresh_service


@shared_task(soft_time_limit=5400, time_limit=5700)
def refresh_bangumi_subjects_task(limit: int | None = None) -> dict:
    """Re-fetch known Bangumi subjects, legacy rows first.

    Bangumi has no changed-since feed, so freshness comes from re-reading what
    we hold; this is also the only way a legacy row (no raw payload, no
    revision) becomes a modern one.
    """
    batch = limit if limit is not None else settings.BANGUMI_SUBJECT_REFRESH_BATCH_SIZE
    return subject_refresh_service.refresh(limit=max(1, int(batch)))


__all__ = ["refresh_bangumi_subjects_task"]
