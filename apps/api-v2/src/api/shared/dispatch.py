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
SYNC_TASK = "apps.sync.tasks.campaigns.run_sync_campaign_task"


def task_for_import(provider: str) -> str | None:
    return IMPORT_TASKS.get(provider)


def import_kwargs(*, external_id: str, include_related: bool, job_id: str) -> dict[str, Any]:
    return {
        "external_id": external_id,
        "include_related": include_related,
        "job_id": job_id,
    }


def _sender() -> Any:
    from celery import Celery

    app = Celery(broker=os.environ.get("CELERY_BROKER_URL", ""))
    return app


def publish(task: str, kwargs: dict[str, Any], *, sender: Any = None) -> str | None:
    """The broker's task id, or None when there is no broker configured."""
    if not os.environ.get("CELERY_BROKER_URL"):
        return None
    app = sender or _sender()
    result = app.send_task(task, kwargs=kwargs)
    return str(result.id)
