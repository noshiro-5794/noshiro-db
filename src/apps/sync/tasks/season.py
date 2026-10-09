from celery import shared_task
from django.conf import settings

from apps.index.services import mal_identity_service
from apps.sync.services.match_apply import match_apply_service
from apps.sync.services.season_pipeline import season_pipeline_service
from apps.sync.services.season_rollover import season_rollover_service


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


@shared_task(soft_time_limit=3600, time_limit=3900)
def apply_match_proposals_task(limit: int | None = None) -> dict:
    """Bind the AI-adjudicated match proposals that pass the evidence gates.

    Generating candidates and evaluating them were both scheduled; applying the
    verdicts was not, so thousands of confident proposals sat pending until an
    admin ran the command by hand. Pairs that fail a gate stay pending for
    review instead of being retired by an unattended pass.
    """
    batch = limit if limit is not None else settings.MATCH_APPLY_BATCH_SIZE
    return match_apply_service.run(
        limit=max(1, int(batch)),
        apply=True,
        abstain_ineligible=False,
    )
