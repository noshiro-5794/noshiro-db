"""Complete manual subject sync with committed leases and atomic graph projection."""

from typing import Any
from uuid import UUID

from celery import current_task, shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index.resolution import cluster_ids
from api.db import fetch
from api.integrations.providers.bangumi import BangumiClient
from api.worker import bangumi_sync, jobs
from api.worker.importing import owns_job
from api.worker.runtime import run
from api.worker.session import session_scope


class SubjectNotFound(LookupError):
    """The requested canonical cluster has no active Bangumi subject representation."""


class SubjectNotSupported(ValueError):
    """The stored provider identifier cannot be used as a Bangumi subject ID."""


class JobLeaseLost(RuntimeError):
    """A manual sync may no longer update the job or catalogue."""


async def subject_identifier(session: AsyncSession, subject_id: str) -> int:
    try:
        identifier = UUID(subject_id)
    except (ValueError, TypeError, AttributeError) as error:
        raise SubjectNotFound("The subject to synchronize was not found.") from error
    members = await cluster_ids(session, identifier)
    rows = await fetch(
        session,
        """
        SELECT p.external_id FROM entity_representation r
        JOIN provider_record p ON p.id=r.provider_record_id
        JOIN provider_namespace ns ON ns.id=p.namespace_id
        JOIN provider source ON source.id=ns.provider_id
        WHERE r.entity_id=ANY(:ids) AND r.is_active AND p.status='active'
          AND source.slug='bangumi' AND ns.slug='subject' ORDER BY r.created_at, r.id LIMIT 1
        """,
        {"ids": list(members)},
    )
    if not rows:
        raise SubjectNotFound("The subject to synchronize was not found.")
    try:
        result = int(rows[0].external_id)
    except (TypeError, ValueError) as error:
        raise SubjectNotSupported("The subject cannot be synchronized.") from error
    if result <= 0:
        raise SubjectNotSupported("The subject cannot be synchronized.")
    return result


async def synchronize(
    *,
    bangumi_id: int | None = None,
    subject_id: str | None = None,
    job_id: str | None = None,
    lease_owner: str,
) -> dict[str, Any]:
    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=lease_owner, lease_seconds=960
        ):
            return {"skipped": True, "reason": "job already claimed"}
        await jobs.mark_running(
            session,
            job_id=job_id,
            total_count=3,
            current_label="Fetching subject",
            lease_owner=lease_owner,
        )
    try:
        async with session_scope() as session:
            if subject_id is not None:
                bangumi_id = await subject_identifier(session, subject_id)
            policy = await fetch(
                session, "SELECT storage_policy FROM provider WHERE slug='bangumi'", {}
            )
        if not isinstance(bangumi_id, int) or isinstance(bangumi_id, bool) or bangumi_id <= 0:
            raise SubjectNotSupported("The subject cannot be synchronized.")

        async def progress(label: str, total: int | None) -> None:
            if job_id is None:
                return
            async with session_scope() as session:
                if not await owns_job(session, job_id, lease_owner):
                    raise JobLeaseLost("Subject sync job lease lost.")
                await jobs.heartbeat(
                    session, job_id=job_id, lease_owner=lease_owner, lease_seconds=960
                )
                await jobs.mark_running(
                    session,
                    job_id=job_id,
                    total_count=total,
                    current_label=label,
                    lease_owner=lease_owner,
                )

        client = BangumiClient()
        client.forbid_storage(forbidden=bool(policy and policy[0].storage_policy == "forbidden"))
        try:
            batch = await bangumi_sync.fetch_batch(client, bangumi_id, progress=progress)
        finally:
            client.close()
        async with session_scope() as session:
            if job_id and not await owns_job(session, job_id, lease_owner):
                raise JobLeaseLost("Subject sync job lease lost.")
            result = await bangumi_sync.project_batch(session, bangumi_id, batch)
            total = 3 + result["character_count"] + result["staff_count"]
            await jobs.set_total(session, job_id=job_id, total_count=total)
            await jobs.advance(
                session,
                job_id=job_id,
                processed=total,
                synced=total,
                current_label="Subject sync completed",
                lease_owner=lease_owner,
            )
            await jobs.mark_succeeded(
                session,
                job_id=job_id,
                result=result,
                current_label="Subject sync completed",
                lease_owner=lease_owner,
            )
            return result
    except Exception as error:
        async with session_scope() as session:
            if job_id and await owns_job(session, job_id, lease_owner):
                await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
        raise


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.manual.sync_subject_by_uuid_task",
    queue="sync",
    soft_time_limit=900,
    time_limit=960,
)
def sync_subject_by_uuid_task(subject_id: str, job_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = run(
        synchronize(
            subject_id=subject_id, job_id=job_id, lease_owner=f"celery:{current_task.request.id}"
        )
    )
    return result


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.manual.sync_subject_by_bangumi_id_task",
    queue="sync",
    soft_time_limit=900,
    time_limit=960,
)
def sync_subject_by_bangumi_id_task(bangumi_id: int, job_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = run(
        synchronize(
            bangumi_id=bangumi_id, job_id=job_id, lease_owner=f"celery:{current_task.request.id}"
        )
    )
    return result
