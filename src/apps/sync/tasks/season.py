from celery import shared_task
from django.conf import settings

from apps.index.services import mal_identity_service
from apps.sync.services.season_pipeline_service import season_pipeline_service
from apps.sync.services.season_rollover_service import season_rollover_service


@shared_task(soft_time_limit=5400, time_limit=6000)
def run_season_pipeline_task(
    *,
    max_items_per_source: int | None = None,
    evaluate: bool = False,
) -> dict:
    return season_pipeline_service.run(
        max_items_per_source=max_items_per_source,
        evaluate=evaluate,
    )


@shared_task(soft_time_limit=6000, time_limit=6600)
def check_season_rollover_task() -> dict:
    return season_rollover_service.run()


@shared_task(soft_time_limit=3600, time_limit=3900)
def reconcile_official_mal_links_task(limit: int | None = None) -> dict:
    """Bind AniList works to their MAL twin through the official id.

    Runs on its own budget because the sweep walks every MAL record. Each pair
    commits separately, so the task can stop at its limit and continue
    tomorrow without losing the bindings it already made.
    """
    batch = limit if limit is not None else settings.MAL_IDENTITY_RECONCILE_BATCH_SIZE
    return mal_identity_service.reconcile_official_links(
        create=True,
        apply=True,
        limit=max(1, int(batch)),
    )
