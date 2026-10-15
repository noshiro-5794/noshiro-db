"""The scheduled sweep that keeps cross-provider work identity moving.

Candidate generation is resumable, so this cadence decides how quickly the
catalogue is walked rather than how much of it is ever seen: each run takes the
next window of source works for anime and galgame, proposes pairs, and hands the
new candidates to the AI evaluator. Nothing is merged here.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.conf import settings

from apps.index.services import provider_candidate_service

EVALUATE_TASK = "apps.ai.tasks.evaluate_match_candidate_task"
LEG_COUNT = 3


@shared_task(soft_time_limit=5400, time_limit=5700)
def sweep_match_candidates_task(limit: int | None = None) -> dict[str, Any]:
    """Advance every candidate sweep by one bounded window.

    The batch is split across the legs so a single run cannot spend its whole
    budget on one catalogue: MAL holds more anime records than AniList, and VNDB
    holds more works than either, so an unsplit sweep would starve the others for
    as long as it took to walk the largest one.
    """
    total = int(limit if limit is not None else settings.MATCH_CANDIDATE_BATCH_SIZE)
    per_leg = max(1, total // LEG_COUNT)
    legs = {
        "anilist_anime": provider_candidate_service.generate_anime_candidates(
            limit=per_leg
        ),
        "mal_anime": provider_candidate_service.generate_mal_bangumi_candidates(
            limit=per_leg
        ),
        "vndb_galgame": provider_candidate_service.generate_galgame_candidates(
            limit=per_leg
        ),
    }
    created = [
        str(candidate_id)
        for leg in legs.values()
        for candidate_id in leg.get("created_ids") or []
    ]
    if created:
        # Imported lazily: the app that owns this task is imported while the
        # Celery app is still being configured.
        from config.celery import app as celery_app

        for candidate_id in created:
            celery_app.send_task(EVALUATE_TASK, args=[candidate_id], queue="ai")
    return {
        "candidates_created": len(created),
        "ai_evaluations_dispatched": len(created),
        "legs": {
            name: {
                "window": leg["window"],
                "skipped": leg["skipped_processed"],
                "cursor_after": leg["cursor_after"],
                "catalogue_size": leg["catalogue_size"],
                "completed_pass": leg["completed_pass"],
                "created": leg["candidates_created"],
                "conflicting": leg["conflicting_pairs"],
            }
            for name, leg in legs.items()
        },
    }


__all__ = ["sweep_match_candidates_task"]
