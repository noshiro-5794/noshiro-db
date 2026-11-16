"""The first tasks the replacement runs itself.

They are registered under the Django names on purpose: `-Q realtime` on either worker
picks up the same messages, so moving one is a container flip, not a release.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from celery import shared_task

from api.contexts.presentation.fragments import fetch
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


async def _scan_stale_sync_states(threshold_seconds: int) -> dict[str, int]:
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(seconds=max(60, threshold_seconds))
    async with session_scope() as session:
        stale = await fetch(
            session,
            "SELECT DISTINCT task_name FROM sync_state WHERE shard = 'main'"
            " AND status = 'running' AND updated_at < :cutoff",
            {"cutoff": cutoff},
        )
        for row in stale:
            await fetch(
                session,
                "UPDATE sync_state SET status = 'failed', fail_count = fail_count + 1,"
                " updated_at = now() WHERE task_name = :name AND shard = 'main'"
                " AND status = 'running' RETURNING id",
                {"name": row.task_name},
            )
            logger.warning("Stale incremental sync state unlocked: %s", row.task_name)
    return {"stale_states": len(stale)}


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.maintenance.scan_stale_sync_states", queue="realtime"
)
def scan_stale_sync_states() -> dict[str, int]:
    import os

    threshold = int(os.environ.get("SYNC_STALE_STATE_SECONDS", "5400"))
    result: dict[str, int] = run(_scan_stale_sync_states(threshold))
    return result


async def _refresh_popularity() -> dict[str, int]:
    from api.worker import catalogue

    async with session_scope() as session:
        scored = await catalogue.refresh(session, now=datetime.now(UTC))
    return {"scored": scored}


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.index.tasks.popularity.refresh_popularity_task", queue="realtime"
)
def refresh_popularity_task() -> dict[str, int]:
    result: dict[str, int] = run(_refresh_popularity())
    return result


async def _import_mal_media(mal_id: int, job_id: str | None, lease_owner: str) -> dict[str, Any]:
    from api.worker import mal_import
    from api.worker.providers.mal import MALClient

    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=lease_owner, lease_seconds=960
        ):
            return {"skipped": True, "reason": "job already claimed"}
        await jobs.mark_running(
            session,
            job_id=job_id,
            total_count=1,
            current_label=f"Importing MAL {mal_id}",
            lease_owner=lease_owner,
        )
        try:
            payload = await asyncio.to_thread(MALClient().fetch_anime, mal_id)
            entity_id = await mal_import.import_anime(session, payload)
            result = {
                "entity_id": str(entity_id),
                "provider": "mal",
                "external_id": mal_id,
            }
            await jobs.advance(
                session,
                job_id=job_id,
                processed=1,
                synced=1,
                current_label=f"Imported MAL {mal_id}",
                lease_owner=lease_owner,
            )
            await jobs.mark_succeeded(
                session, job_id=job_id, result=result, lease_owner=lease_owner
            )
            return result
        except Exception as error:
            await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
            raise


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.mal.import_mal_media_task",
    queue="sync",
    soft_time_limit=900,
    time_limit=960,
)
def import_mal_media_task(mal_id: int, *, job_id: str | None = None) -> dict[str, Any]:
    from celery import current_task

    lease_owner = f"celery:{current_task.request.id}"
    result: dict[str, Any] = run(_import_mal_media(mal_id, job_id, lease_owner))
    return result


async def _reconcile_official_mal_links(limit: int | None) -> dict[str, int]:
    from api.worker import mal_identity

    async with session_scope() as session:
        result = await mal_identity.bind(session, create=True, apply=True, limit=limit)
    return result


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.season.reconcile_official_mal_links_task", queue="sync"
)
def reconcile_official_mal_links_task(limit: int | None = None) -> dict[str, int]:
    """Bind MAL works to their AniList twin through the official id."""
    batch = (
        limit
        if limit is not None
        else int(os.environ.get("MAL_IDENTITY_RECONCILE_BATCH_SIZE", "2000"))
    )
    result: dict[str, int] = run(_reconcile_official_mal_links(max(1, batch)))
    return result


async def _sync_calendar(job_id: str | None, lease_owner: str) -> dict[str, Any]:
    from api.worker import calendar_sync
    from api.worker.providers.bangumi import BangumiClient

    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=lease_owner, lease_seconds=3900
        ):
            return {"skipped": True, "reason": "job already claimed"}
        await jobs.mark_running(
            session,
            job_id=job_id,
            total_count=0,
            current_label="Fetching calendar",
            lease_owner=lease_owner,
        )
        try:
            payload = await asyncio.to_thread(BangumiClient().fetch_calendar)
            result = await calendar_sync.sync_calendar(session, _Prefetched(payload))
            await jobs.advance(
                session,
                job_id=job_id,
                processed=1,
                current_label="Calendar board replaced",
                lease_owner=lease_owner,
            )
            await jobs.mark_succeeded(
                session, job_id=job_id, result=result, lease_owner=lease_owner
            )
            return result
        except Exception as error:
            await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
            raise


class _Prefetched:
    """Adapter so the flow can be driven by a payload fetched off-thread."""

    def __init__(self, payload: list[Any]) -> None:
        self._payload = payload

    def fetch_calendar(self) -> list[Any]:
        return self._payload


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.calendar.sync_calendar_task",
    queue="sync",
    soft_time_limit=3600,
    time_limit=3900,
)
def sync_calendar_task(
    sync_subject_details: bool = False, job_id: str | None = None
) -> dict[str, Any]:
    """Replace the weekly board. Subject-detail syncing is not ported yet."""
    if sync_subject_details:
        raise RuntimeError(
            "sync_subject_details=True is not implemented in the replacement yet; "
            "the board itself is."
        )
    from celery import current_task

    lease_owner = f"celery:{current_task.request.id}"
    result: dict[str, Any] = run(_sync_calendar(job_id, lease_owner))
    return result


async def _refresh_bangumi_subjects(limit: int) -> dict[str, Any]:
    from api.worker import subject_refresh
    from api.worker.providers.bangumi import BangumiClient

    async with session_scope() as session:
        return await subject_refresh.refresh(session, BangumiClient(), limit=limit)


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.refresh.refresh_bangumi_subjects_task",
    queue="sync",
    soft_time_limit=5400,
    time_limit=5700,
)
def refresh_bangumi_subjects_task(limit: int | None = None) -> dict[str, Any]:
    """Re-fetch known Bangumi subjects, legacy rows first."""
    batch = (
        limit
        if limit is not None
        else int(os.environ.get("BANGUMI_SUBJECT_REFRESH_BATCH_SIZE", "500"))
    )
    result: dict[str, Any] = run(_refresh_bangumi_subjects(max(1, batch)))
    return result


async def _import_anilist_media(
    anilist_id: int, job_id: str | None, lease_owner: str
) -> dict[str, Any]:
    import api.worker.anilist_import as anilist_import
    from api.worker.providers.anilist import AniListClient

    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=lease_owner, lease_seconds=900
        ):
            return {"skipped": True, "reason": "job already claimed"}
        await jobs.mark_running(
            session,
            job_id=job_id,
            total_count=1,
            current_label=f"Importing AniList {anilist_id}",
            lease_owner=lease_owner,
        )
        try:
            media = await asyncio.to_thread(AniListClient().fetch_media, anilist_id)
            entity_id = await anilist_import.import_media(session, media)
            result = {
                "entity_id": str(entity_id),
                "provider": "anilist",
                "external_id": anilist_id,
            }
            await jobs.advance(
                session,
                job_id=job_id,
                processed=1,
                synced=1,
                current_label=f"Imported AniList {anilist_id}",
                lease_owner=lease_owner,
            )
            await jobs.mark_succeeded(
                session, job_id=job_id, result=result, lease_owner=lease_owner
            )
            return result
        except Exception as error:
            await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
            raise


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.anilist.import_anilist_media_task",
    queue="sync",
    soft_time_limit=900,
    time_limit=960,
)
def import_anilist_media_task(anilist_id: int, *, job_id: str | None = None) -> dict[str, Any]:
    """Import one AniList media by id, under the name the dispatcher publishes."""
    from celery import current_task

    lease_owner = f"celery:{current_task.request.id}"
    result: dict[str, Any] = run(_import_anilist_media(anilist_id, job_id, lease_owner))
    return result


async def _run_airing_daily(
    batch_size: int | None, job_id: str | None, lease_owner: str
) -> dict[str, Any]:
    from datetime import UTC, datetime

    import api.worker.airing_daily as airing_daily
    import api.worker.anilist_import as anilist_import
    import api.worker.mal_import as mal_import
    import api.worker.subject_import as subject_import
    from api.worker.providers.anilist import AniListClient
    from api.worker.providers.bangumi import BangumiClient
    from api.worker.providers.mal import MALClient

    mal = MALClient()
    anilist = AniListClient()
    bangumi = BangumiClient()

    async def fetch_media(external_id: int) -> dict[str, Any]:
        # The caller knows which provider the target belongs to only by the importer it
        # ends up in, so this resolves against whichever client answers.
        try:
            return await asyncio.to_thread(mal.fetch_anime, external_id)
        except Exception:
            return await asyncio.to_thread(anilist.fetch_media, external_id)

    async def fetch_subject(external_id: int) -> dict[str, Any]:
        return await asyncio.to_thread(bangumi.fetch_subject, external_id)

    async def import_anime(session: Any, media: dict[str, Any]) -> None:
        await mal_import.import_anime(session, media)

    async def import_media(session: Any, media: dict[str, Any]) -> None:
        await anilist_import.import_media(session, media)

    async def import_subject(session: Any, subject: dict[str, Any]) -> None:
        await subject_import.import_subject(session, subject)

    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=lease_owner, lease_seconds=2100
        ):
            return {"skipped": True, "reason": "job already claimed"}
        await jobs.mark_running(
            session,
            job_id=job_id,
            total_count=0,
            current_label="Refreshing the airing board",
            lease_owner=lease_owner,
        )
        try:
            result = await airing_daily.sync_day(
                session,
                now=datetime.now(UTC),
                batch_size=batch_size or int(os.environ.get("AIRING_DAILY_BATCH_SIZE", "100")),
                fetch_media=fetch_media,
                fetch_subject=fetch_subject,
                import_anime=import_anime,
                import_media=import_media,
                import_subject=import_subject,
            )
            await jobs.mark_succeeded(
                session, job_id=job_id, result=result, lease_owner=lease_owner
            )
            return result
        except Exception as error:
            await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
            raise


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.airing.run_airing_daily_task",
    queue="sync",
    soft_time_limit=1800,
    time_limit=2100,
)
def run_airing_daily_task(
    batch_size: int | None = None, job_id: str | None = None
) -> dict[str, Any]:
    """Refresh one window of the airing board, oldest state first."""
    from celery import current_task

    lease_owner = f"celery:{current_task.request.id}"
    result: dict[str, Any] = run(_run_airing_daily(batch_size, job_id, lease_owner))
    return result
