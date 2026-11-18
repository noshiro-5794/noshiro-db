"""The worker runtime: the replacement's own Celery application.

It registers the same task names the Django workers answer to, on the same queues, so a
task published by either service can be consumed by either worker. That is what makes the
migration a queue-by-queue flip instead of a coordinated release.
"""

from __future__ import annotations

import os

from celery import Celery

from api.worker import (  # noqa: F401  registers the tasks
    ai_tasks,
    calendar_tasks,
    campaign_tasks,
    frontier_tasks,
    incremental_tasks,
    mail_tasks,
    manual_sync,
    match_application,
    matching_tasks,
    season_tasks,
    tasks,
    vndb_tasks,
)

app = Celery("noshiro-worker", broker=os.environ.get("CELERY_BROKER_URL", ""))

app.conf.update(
    task_default_queue="realtime",
    task_routes={
        "apps.sync.tasks.*": {"queue": "sync"},
        "apps.ai.tasks.*": {"queue": "ai"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    timezone=os.environ.get("TZ", "Asia/Shanghai"),
    enable_utc=True,
)
