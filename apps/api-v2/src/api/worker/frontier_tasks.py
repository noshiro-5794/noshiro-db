"""Scheduled discovery of MAL and Bangumi catalogue boundaries."""

from __future__ import annotations

import os
from typing import Any

from celery import current_task, shared_task

from api.worker import frontier, jobs
from api.worker.providers.bangumi import BangumiClient
from api.worker.providers.mal import MALClient
from api.worker.runtime import run
from api.worker.session import session_scope


async def probe_frontiers(job_id: str | None, lease_owner: str) -> dict[str, Any]:
    async with session_scope() as session:
        if job_id and not await jobs.claim(
            session, job_id=job_id, lease_owner=lease_owner, lease_seconds=1900
        ):
            return {"skipped": True, "reason": "job already claimed"}
        await jobs.mark_running(
            session,
            job_id=job_id,
            total_count=2,
            current_label="Probing provider frontiers",
            lease_owner=lease_owner,
        )
        mal = MALClient()
        bangumi = BangumiClient()
        try:
            results = []
            for provider, namespace, fetcher, floor in (
                ("mal", "anime", mal.fetch_anime, int(os.environ.get("MAL_MAX_ANIME_ID", "65500"))),
                ("bangumi", "subject", bangumi.fetch_subject, 0),
            ):
                seed = max(
                    floor,
                    await frontier.highest_stored_id(
                        session,
                        provider_slug=provider,
                        namespace_slug=namespace,
                    ),
                )
                results.append(
                    await frontier.probe_frontier(
                        session,
                        provider_slug=provider,
                        namespace_slug=namespace,
                        fetch=fetcher,
                        seed=seed,
                        window=int(os.environ.get("PROVIDER_FRONTIER_PROBE_WINDOW", "500")),
                        max_misses=int(os.environ.get("PROVIDER_FRONTIER_MAX_MISSES", "50")),
                    )
                )
            result = {"frontiers": results}
            await jobs.mark_succeeded(
                session,
                job_id=job_id,
                result=result,
                current_label="Provider frontiers probed",
                lease_owner=lease_owner,
            )
            return result
        except Exception as error:
            await jobs.mark_failed(session, job_id=job_id, error=error, lease_owner=lease_owner)
            raise


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.frontier.probe_provider_frontiers_task",
    queue="sync",
    soft_time_limit=1800,
    time_limit=1900,
)
def probe_provider_frontiers_task(job_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = run(probe_frontiers(job_id, f"celery:{current_task.request.id}"))
    return result
