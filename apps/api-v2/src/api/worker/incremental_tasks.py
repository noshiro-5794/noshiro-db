"""Incremental Bangumi imports with per-item source and cursor transactions."""

import asyncio
import logging
import os
from contextlib import suppress
from typing import Any

from celery import current_task, shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization import incremental
from api.contexts.synchronization.domain import LeaseLost
from api.worker import bangumi_entities, bangumi_episodes, bangumi_relations, jobs
from api.worker.importing import owns_job
from api.worker.providers.bangumi import BangumiClient
from api.worker.providers.errors import ProviderError
from api.worker.runtime import run
from api.worker.session import session_scope
from api.worker.subject_import import import_subject, provide_subject

logger = logging.getLogger(__name__)


def fetch_source(client: BangumiClient, part: incremental.Part, identifier: int) -> Any:
    if part == "subject":
        return client.fetch_subject(identifier)
    if part == "character":
        return client.fetch_character(identifier)
    if part == "person":
        return client.fetch_person(identifier)
    if part == "subjects":
        return client.fetch_subject_subjects(identifier)
    if part == "staff":
        return client.fetch_subject_persons(identifier)
    if part == "characters":
        return client.fetch_subject_characters(identifier)
    items = []
    offset = 0
    while True:
        page = client.fetch_subject_episodes(subject_id=identifier, limit=100, offset=offset)
        data = page.get("data")
        if not isinstance(data, list):
            raise ProviderError("Bangumi episode response is missing data.")
        items.extend(data)
        if len(data) < 100:
            return items
        offset += 100


async def project(
    session: AsyncSession, part: incremental.Part, identifier: int, payload: Any
) -> None:
    if part == "subject":
        await import_subject(session, payload)
    elif part == "character" or part == "person":
        await bangumi_entities.import_entity(session, payload, part)
    else:
        work = await provide_subject(session, str(identifier))
        if part == "episodes":
            await bangumi_episodes.import_episodes(session, work, str(identifier), payload)
        else:
            await bangumi_relations.import_relations(
                session,
                work,
                str(identifier),
                subjects=payload if part == "subjects" else None,
                staff=payload if part == "staff" else None,
                characters=payload if part == "characters" else None,
            )


async def own_job(session: AsyncSession, job_id: str | None, owner: str) -> None:
    if job_id and not await owns_job(session, job_id, owner):
        raise LeaseLost("Incremental sync job lease lost.")


async def sync_task(
    config: incremental.TaskConfig,
    batch_size: int,
    client: BangumiClient,
    *,
    job_id: str | None,
    owner: str,
    reset_total: bool,
) -> dict[str, Any]:
    async with session_scope() as session:
        await own_job(session, job_id, owner)
        await jobs.mark_running(
            session,
            job_id=job_id,
            total_count=batch_size if reset_total else None,
            current_label=f"Starting {config.name}",
            lease_owner=owner,
        )
        window = await incremental.start_window(session, config, batch_size)
    result: dict[str, Any] = {
        "task_name": config.name,
        "shard": "main",
        "start_id": window.start,
        "end_id": window.end,
        "processed_count": 0,
        "synced_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
    }
    last_synced = window.start - 1
    errors = skips = 0
    try:
        for identifier in range(window.start, window.end + 1):
            async with session_scope() as session:
                await own_job(session, job_id, owner)
                await incremental.owned(session, window)
                eligible = not config.requires_subject or await incremental.subject_exists(
                    session, identifier
                )
                policy = await fetch(
                    session, "SELECT storage_policy FROM provider WHERE slug='bangumi'", {}
                )
            client.forbid_storage(
                forbidden=bool(policy and policy[0].storage_policy == "forbidden")
            )
            outcome = "skipped"
            error: Exception | None = None
            if eligible:
                try:
                    payload = await asyncio.to_thread(fetch_source, client, config.part, identifier)
                    async with session_scope() as session:
                        await own_job(session, job_id, owner)
                        await incremental.owned(session, window)
                        await project(session, config.part, identifier, payload)
                        version = await incremental.advance(session, window, identifier)
                        await jobs.advance(
                            session,
                            job_id=job_id,
                            synced=1,
                            current_label=f"{config.name}: {identifier} synced",
                            lease_owner=owner,
                        )
                    window.version = version
                    outcome = "synced"
                except LeaseLost:
                    raise
                except ProviderError as caught:
                    if not caught.is_not_found:
                        error = caught
                except Exception as caught:
                    error = caught
            if outcome != "synced":
                outcome = "failed" if error is not None else "skipped"
                async with session_scope() as session:
                    await own_job(session, job_id, owner)
                    await incremental.owned(session, window)
                    if error is not None:
                        logger.warning(
                            "Incremental source import failed",
                            extra={
                                "task_name": config.name,
                                "external_id": identifier,
                                "error_type": type(error).__name__,
                            },
                        )
                        await incremental.record_error(session, config.name, identifier)
                    version = await incremental.advance(session, window, last_synced)
                    await jobs.advance(
                        session,
                        job_id=job_id,
                        synced=0,
                        skipped=int(outcome == "skipped"),
                        failed=int(outcome == "failed"),
                        current_label=f"{config.name}: {identifier} {outcome}",
                        lease_owner=owner,
                    )
                window.version = version
            result["processed_count"] += 1
            result[f"{outcome}_count"] += 1
            if outcome == "failed":
                errors += 1
            else:
                errors = 0
                if outcome == "synced":
                    last_synced = identifier
                    skips = 0
                else:
                    skips += 1
            if skips >= max(1, int(os.environ.get("SYNC_INCREMENTAL_MAX_CONSECUTIVE_SKIPS", "50"))):
                result["frontier_reached"] = True
                break
            if errors >= max(
                1, int(os.environ.get("SYNC_INCREMENTAL_MAX_CONSECUTIVE_ERRORS", "20"))
            ):
                raise RuntimeError("Too many consecutive incremental sync errors.")
        current = last_synced if result.get("frontier_reached") else window.end
        async with session_scope() as session:
            await own_job(session, job_id, owner)
            await incremental.advance(session, window, current, status="finished")
        return result
    except Exception:
        async with session_scope() as session:
            with suppress(LeaseLost):
                await incremental.advance(session, window, last_synced, status="failed")
        raise


async def execute(
    *, task_name: str | None, batch_size: int | None, job_id: str | None, owner: str
) -> dict[str, Any]:
    names = [task_name] if task_name else list(incremental.CONFIGS)
    if any(name not in incremental.CONFIGS for name in names):
        raise ValueError(f"Unknown incremental sync task: {task_name}")
    size = max(1, int(batch_size or os.environ.get("SYNC_INCREMENTAL_SUBJECT_BATCH_SIZE", "1000")))
    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=owner, lease_seconds=3900
        ):
            return {"skipped": True, "reason": "job already claimed"}
        if not task_name:
            await jobs.mark_running(
                session,
                job_id=job_id,
                total_count=len(names) * size,
                current_label="Starting incremental sync",
                lease_owner=owner,
            )
    client = BangumiClient()
    try:
        results = [
            await sync_task(
                incremental.CONFIGS[name],
                size,
                client,
                job_id=job_id,
                owner=owner,
                reset_total=bool(task_name),
            )
            for name in names
        ]
        result = results[0] if task_name else {"results": results}
        async with session_scope() as session:
            await own_job(session, job_id, owner)
            await jobs.mark_succeeded(
                session,
                job_id=job_id,
                result=result,
                current_label="Incremental sync completed",
                lease_owner=owner,
            )
        return result
    except Exception as error:
        async with session_scope() as session:
            await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=owner)
        raise
    finally:
        client.close()


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.incremental.run_incremental_sync_task",
    queue="sync",
    soft_time_limit=3600,
    time_limit=3900,
)
def run_incremental_sync_task(
    task_name: str | None = None, batch_size: int | None = None, job_id: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = run(
        execute(
            task_name=task_name,
            batch_size=batch_size,
            job_id=job_id,
            owner=f"celery:{current_task.request.id}",
        )
    )
    return result
