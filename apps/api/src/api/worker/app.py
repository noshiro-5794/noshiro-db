"""Register Celery tasks, queue routing, and the periodic schedule.

Task names are the broker protocol. Keep them stable across Python module moves so
queued messages can be delivered during a rolling release.
"""

from __future__ import annotations

import os

from celery import Celery

from api.worker.schedule import periodic_tasks
from api.worker.tasks import (  # noqa: F401
    ai,
    calendar,
    campaigns,
    frontier,
    incremental,
    linking,
    mail,
    maintenance,
    manual_sync,
    match_application,
    matching,
    seasons,
    vndb,
)

app = Celery("noshiro-worker", broker=os.environ.get("CELERY_BROKER_URL", ""))

app.conf.update(
    task_default_queue="realtime",
    task_queues={
        name: {"exchange": name, "routing_key": name} for name in ("realtime", "sync", "ai")
    },
    beat_schedule=periodic_tasks(),
    broker_transport_options={
        "visibility_timeout": int(os.environ.get("CELERY_VISIBILITY_TIMEOUT", "7200"))
    },
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_time_limit=30,
    task_soft_time_limit=20,
    task_default_retry_delay=60,
    task_routes={
        "apps.sync.tasks.maintenance.*": {"queue": "realtime"},
        "apps.sync.tasks.*": {"queue": "sync"},
        "apps.ai.tasks.*": {"queue": "ai"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    timezone=os.environ.get("TZ", "Asia/Shanghai"),
    enable_utc=True,
)
