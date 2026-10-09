from celery import shared_task

from apps.index.services import popularity_service


@shared_task(soft_time_limit=1800, time_limit=1980)
def refresh_popularity_task() -> dict:
    """Rebuild the catalogue's popularity ranking after the daily syncs."""
    scored = popularity_service.refresh()
    return {"scored": scored}
