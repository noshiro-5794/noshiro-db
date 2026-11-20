"""Leased weekly calendar synchronization with independent subject failure reporting."""

import asyncio
import logging
from typing import Any

from celery import current_task, shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.worker import bangumi_sync, calendar_sync, jobs
from api.worker import calendar as calendar_read
from api.worker.calendar_images import CalendarImages
from api.worker.importing import owns_job
from api.worker.manual_sync import JobLeaseLost
from api.worker.providers.bangumi import BangumiClient
from api.worker.runtime import run
from api.worker.session import session_scope
from api.worker.subject_import import import_subject

logger = logging.getLogger(__name__)


async def record_error(session: AsyncSession, subject_id: int) -> None:
    await fetch(
        session,
        """
        INSERT INTO sync_error
          (task_name,entity_id,retry_count,first_occurred_at,last_occurred_at)
        VALUES ('calendar',:id,0,now(),now())
        ON CONFLICT (task_name,entity_id) DO UPDATE SET
          retry_count=sync_error.retry_count+1,last_occurred_at=now() RETURNING id
        """,
        {"id": subject_id},
    )


async def synchronize(
    *, sync_subject_details: bool, job_id: str | None, lease_owner: str
) -> dict[str, Any]:
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

    async def progress(label: str, total: int | None = None) -> None:
        async with session_scope() as session:
            if job_id and not await owns_job(session, job_id, lease_owner):
                raise JobLeaseLost("Calendar sync job lease lost.")
            await jobs.heartbeat(
                session, job_id=job_id, lease_owner=lease_owner, lease_seconds=3900
            )
            await jobs.mark_running(
                session,
                job_id=job_id,
                total_count=total,
                current_label=label,
                lease_owner=lease_owner,
            )

    async def advance(subject_id: int, *, failed: bool = False, synced: bool = True) -> None:
        async with session_scope() as session:
            if job_id and not await owns_job(session, job_id, lease_owner):
                raise JobLeaseLost("Calendar sync job lease lost.")
            if failed:
                await record_error(session, subject_id)
            await jobs.advance(
                session,
                job_id=job_id,
                synced=int(synced and not failed),
                failed=1 if failed else 0,
                current_label=f"Calendar subject {subject_id}",
                lease_owner=lease_owner,
            )

    client = BangumiClient()
    images: CalendarImages | None = None
    try:
        images = CalendarImages()
        async with session_scope() as session:
            policy = await fetch(
                session, "SELECT storage_policy FROM provider WHERE slug='bangumi'", {}
            )
        client.forbid_storage(forbidden=bool(policy and policy[0].storage_policy == "forbidden"))
        data = await asyncio.to_thread(client.fetch_calendar)
        items = calendar_read.calendar_items(data)
        if not items:
            raise calendar_sync.CalendarError(
                "Bangumi calendar response did not contain any valid subjects."
            )
        await progress("Syncing calendar subjects", len(items))
        works = {}
        prepared = []
        failed_subject_count = 0
        for item in items:
            subject_id = item["id"]
            await progress(f"Fetching calendar subject {subject_id}")
            try:
                subject = await asyncio.to_thread(client.fetch_subject, subject_id)
                async with session_scope() as session:
                    if job_id and not await owns_job(session, job_id, lease_owner):
                        raise JobLeaseLost("Calendar sync job lease lost.")
                    work_id = await import_subject(session, subject)
                works[subject_id] = work_id
                prepared.append(subject_id)
                await asyncio.to_thread(images.cache_cover, subject_id, item.get("images"))
            except JobLeaseLost:
                raise
            except Exception:
                failed_subject_count += 1
                logger.exception("Calendar subject sync failed", extra={"subject_id": subject_id})
                await advance(subject_id, failed=True)
                continue
            await advance(subject_id)

        async with session_scope() as session:
            if job_id and not await owns_job(session, job_id, lease_owner):
                raise JobLeaseLost("Calendar sync job lease lost.")
            written = await calendar_sync.apply_calendar(session, data, prepared_works=works)
            await jobs.set_total(
                session,
                job_id=job_id,
                total_count=len(items) + (len(prepared) if sync_subject_details else 0),
                current_label="Calendar rows refreshed",
            )

        async def detail_progress(label: str, total: int | None) -> None:
            await progress(label)

        detail_synced_count = 0
        detail_failed_count = 0
        if sync_subject_details:
            for subject_id in prepared:
                await progress(f"Fetching calendar subject details {subject_id}")
                try:
                    batch = await bangumi_sync.fetch_batch(
                        client, subject_id, progress=detail_progress
                    )
                    async with session_scope() as session:
                        if job_id and not await owns_job(session, job_id, lease_owner):
                            raise JobLeaseLost("Calendar sync job lease lost.")
                        await bangumi_sync.project_batch(session, subject_id, batch)
                    detail_synced_count += 1
                except JobLeaseLost:
                    raise
                except Exception:
                    detail_failed_count += 1
                    logger.exception(
                        "Calendar subject detail sync failed", extra={"subject_id": subject_id}
                    )
                    await advance(subject_id, failed=True)
                    continue
                await advance(subject_id, synced=False)

        async with session_scope() as session:
            if job_id and not await owns_job(session, job_id, lease_owner):
                raise JobLeaseLost("Calendar sync job lease lost.")
            board = (
                await fetch(
                    session,
                    "SELECT b.id,b.season_key,b.item_count,b.updated_at,o.observed_at "
                    "FROM airing_board b LEFT JOIN provider_observation o ON o.id=b.observation_id "
                    "WHERE b.id=:id",
                    {"id": written["board_id"]},
                )
            )[0]
            result = {
                "weekday_count": len(data),
                "item_count": len(items),
                "synced_subject_count": len(prepared),
                "failed_subject_count": failed_subject_count,
                "detail_synced_count": detail_synced_count,
                "detail_failed_count": detail_failed_count,
                "season_key": written["season_key"],
                "added_subject_count": written["added"],
                "removed_subject_count": written["removed"],
                "added_subject_ids": written["added_subject_ids"],
                "removed_subject_ids": written["removed_subject_ids"],
                "board": {
                    "board_id": str(board.id),
                    "season_key": board.season_key,
                    "item_count": board.item_count,
                    "observed_at": board.observed_at.isoformat() if board.observed_at else None,
                    "refreshed_at": board.updated_at.isoformat(),
                },
            }
            await jobs.mark_succeeded(
                session,
                job_id=job_id,
                result=result,
                current_label="Calendar sync completed",
                lease_owner=lease_owner,
            )
            return result
    except Exception as error:
        async with session_scope() as session:
            if job_id and await owns_job(session, job_id, lease_owner):
                await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
        raise
    finally:
        try:
            client.close()
        finally:
            if images is not None:
                images.close()


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.calendar.sync_calendar_task",
    queue="sync",
    soft_time_limit=3600,
    time_limit=3900,
)
def sync_calendar_task(
    sync_subject_details: bool = False, job_id: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = run(
        synchronize(
            sync_subject_details=sync_subject_details,
            job_id=job_id,
            lease_owner=f"celery:{current_task.request.id}",
        )
    )
    return result
