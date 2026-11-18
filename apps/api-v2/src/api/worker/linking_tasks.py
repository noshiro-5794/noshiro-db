"""Scheduled provider identity retrieval with reviewable search proposals."""

import os
from typing import Any

from celery import shared_task

from api.contexts.matching import bangumi_link
from api.worker.runtime import run


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.linking.link_bangumi_works_task",
    queue="sync",
    soft_time_limit=3600,
    time_limit=3900,
)
def link_bangumi_works_task(limit: int | None = None, force: bool = False) -> dict[str, Any]:
    maximum = max(
        1, int(limit if limit is not None else os.environ.get("BANGUMI_LINK_BATCH_SIZE", "50"))
    )
    result: dict[str, Any] = run(bangumi_link.run_missing(limit=maximum, apply=False, force=force))
    return result
