"""Bounded application of already evaluated matching proposals."""

from __future__ import annotations

import os
from typing import Any

from celery import shared_task

from api.contexts.matching.batch import apply_proposals
from api.worker.runtime import run
from api.worker.session import session_scope


async def apply_batch(limit: int | None) -> dict[str, Any]:
    batch = limit if limit is not None else int(os.environ.get("MATCH_APPLY_BATCH_SIZE", "200"))
    async with session_scope() as session:
        return await apply_proposals(
            session, limit=max(1, batch), apply=True, abstain_ineligible=False
        )


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.season.apply_match_proposals_task",
    queue="sync",
    soft_time_limit=3600,
    time_limit=3900,
)
def apply_match_proposals_task(limit: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = run(apply_batch(limit))
    return result
