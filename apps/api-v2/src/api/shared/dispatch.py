"""Handing work to the worker the old service already runs.

Publishing is separated from sending so the task name and the arguments can be
tested without a broker. The names are Celery's defaults for the Django modules,
which is what makes one worker able to serve both services.
"""

from __future__ import annotations

import os
from typing import Any

IMPORT_TASKS = {
    "vndb": "apps.sync.tasks.vndb.import_vndb_work_task",
    "anilist": "apps.sync.tasks.anilist.import_anilist_work_task",
}
SYNC_TASK = "apps.sync.tasks.campaign.run_sync_campaign_task"


def task_for_import(provider: str) -> str | None:
    return IMPORT_TASKS.get(provider)


IMPORT_ARG = {"vndb": "vndb_id", "anilist": "anilist_id"}


def import_kwargs(
    *, provider: str, external_id: str, include_related: bool, job_id: str
) -> dict[str, Any]:
    """The keyword the task expects is named after the provider, not `external_id`."""
    return {
        IMPORT_ARG[provider]: external_id,
        "include_related": include_related,
        "job_id": job_id,
    }


def _sender() -> Any:
    from celery import Celery

    app = Celery(broker=os.environ.get("CELERY_BROKER_URL", ""))
    return app


def queue_for(task: str) -> str:
    """The queue the old service's routes put this task on."""
    if task.startswith("apps.sync.tasks."):
        return "sync"
    if task.startswith("apps.ai.tasks."):
        return "ai"
    return "realtime"


def publish(
    task: str, kwargs: dict[str, Any], *, queue: str | None = None, sender: Any = None
) -> str | None:
    """The broker's task id, or None when there is no broker configured.

    The queue is not optional in practice: the workers run with `-Q` and the default
    queue is `realtime`, so a task published without one is never consumed.
    """
    if not os.environ.get("CELERY_BROKER_URL"):
        return None
    app = sender or _sender()
    result = app.send_task(task, kwargs=kwargs, queue=queue or queue_for(task))
    return str(result.id)


def sync_kwargs(*, campaign_id: str) -> dict[str, Any]:
    return {"campaign_id": campaign_id}
