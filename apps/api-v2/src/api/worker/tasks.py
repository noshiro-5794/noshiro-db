"""The first tasks the replacement runs itself.

They are registered under the Django names on purpose: `-Q realtime` on either worker
picks up the same messages, so moving one is a container flip, not a release.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from celery import shared_task

from api.worker import jobs
from api.worker.runtime import run
from api.worker.session import session_scope

logger = logging.getLogger(__name__)


async def _scan_stale_sync_jobs() -> dict[str, int]:
    async with session_scope() as session:
        stale = await jobs.stale_running_jobs(session)
        for row in stale:
            await jobs.mark_failed(
                session,
                job_id=row.id,
                error=(
                    f"Lease expired while running (attempt={row.attempt}, "
                    f"lease_owner={row.lease_owner or ''}, "
                    f"celery_task_id={row.celery_task_id or ''})."
                ),
                current_label="Lease expired",
            )
    return {"stale_jobs": len(stale)}


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.maintenance.scan_stale_sync_jobs", queue="realtime"
)
def scan_stale_sync_jobs() -> dict[str, int]:
    result: dict[str, int] = run(_scan_stale_sync_jobs())
    return result


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.maintenance.worker_heartbeat", queue="realtime"
)
def worker_heartbeat() -> dict[str, str | bool]:
    """Publish the beat heartbeat where the API's health page looks for it."""
    from redis import Redis

    now = datetime.now(UTC)
    url = os.environ.get("REDIS_CACHE_URL") or os.environ.get("CELERY_BROKER_URL", "")
    if not url:
        return {"heartbeat_at": now.isoformat(), "published": False}
    Redis.from_url(url).set("noshiro:beat:heartbeat", now.isoformat(), ex=180)
    return {"heartbeat_at": now.isoformat(), "published": True}
