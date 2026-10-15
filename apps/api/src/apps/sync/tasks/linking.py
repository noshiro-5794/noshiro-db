from celery import shared_task
from django.conf import settings

from apps.sync.services.bangumi_link import bangumi_link_service
from apps.sync.services.mal_link_recall import mal_link_recall_service


@shared_task(soft_time_limit=3600, time_limit=3900)
def link_bangumi_works_task(limit: int | None = None, force: bool = False) -> dict:
    """Bind MAL-anchored works to a Bangumi subject the model selected.

    The sweep only becomes coverage if it runs on a clock: the management
    command existed, no beat entry called it, and the MAL-to-Bangumi link count
    stayed at the handful an operator had run by hand. Candidates stay pending
    for the adjudicator instead of binding here, so an unattended pass cannot
    merge two works on the model's word alone.
    """
    batch = limit if limit is not None else settings.BANGUMI_LINK_BATCH_SIZE
    return bangumi_link_service.run_missing(
        limit=max(1, int(batch)),
        apply=False,
        force=force,
    )


@shared_task(soft_time_limit=3600, time_limit=3900)
def recall_mal_links_task(limit: int | None = None, force: bool = False) -> dict:
    """Recall MAL ids for active board works the SQL matcher could not pair.

    Each work costs a full agent loop of database and MAL API searches, so the
    batch is small and the task repeats through the day; works an earlier pass
    concluded are skipped without spending the batch.
    """
    batch = limit if limit is not None else settings.MAL_LINK_RECALL_BATCH_SIZE
    return mal_link_recall_service.run_missing(
        limit=max(1, int(batch)),
        evaluate=True,
        force=force,
    )


__all__ = ["link_bangumi_works_task", "recall_mal_links_task"]
