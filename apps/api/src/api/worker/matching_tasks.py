"""Scheduled candidate generation across the three supported provider legs."""

from __future__ import annotations

import os
from typing import Any

from celery import shared_task

from api.shared.dispatch import publish
from api.worker.candidates import ProviderCandidateService
from api.worker.runtime import run
from api.worker.session import session_scope

EVALUATE_TASK = "apps.ai.tasks.evaluate_match_candidate_task"


async def sweep(limit: int | None) -> dict[str, Any]:
    total = int(
        limit if limit is not None else os.environ.get("MATCH_CANDIDATE_BATCH_SIZE", "2000")
    )
    per_leg = max(1, total // 3)
    async with session_scope() as session:
        service = ProviderCandidateService(session)
        legs = {
            "anilist_anime": await service.generate_anime_candidates(limit=per_leg),
            "mal_anime": await service.generate_mal_bangumi_candidates(limit=per_leg),
            "vndb_galgame": await service.generate_galgame_candidates(limit=per_leg),
        }
    # Publish after commit so a worker never receives an id whose transaction is still open.
    created = [str(value) for leg in legs.values() for value in leg["created_ids"]]
    dispatched = 0
    for candidate_id in created:
        if publish(EVALUATE_TASK, {"candidate_id": candidate_id}, queue="ai"):
            dispatched += 1
    return {
        "candidates_created": len(created),
        "ai_evaluations_dispatched": dispatched,
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


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.matching.sweep_match_candidates_task",
    queue="sync",
    soft_time_limit=5400,
    time_limit=5700,
)
def sweep_match_candidates_task(limit: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = run(sweep(limit))
    return result
