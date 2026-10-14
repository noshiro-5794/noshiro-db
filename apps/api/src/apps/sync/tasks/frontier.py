"""Discover where each provider's id space currently ends.

The sweeps that enumerate MAL and Bangumi stop at a frontier; this is what moves
it. One task walks every provider that needs it, and a provider outage ends that
walk where it stands instead of being mistaken for the end of the catalogue.
"""

from celery import current_task, shared_task
from django.conf import settings

from apps.sync.providers.bangumi import (
    BANGUMI_SOURCE,
    BANGUMI_SUBJECT_NAMESPACE,
    bangumi_client,
)
from apps.sync.providers.frontier import highest_stored_id, probe_frontier
from apps.sync.providers.mal import MAL_ANIME_NAMESPACE, MAL_SOURCE, mal_api_client
from apps.sync.services.sync_job import sync_job_service


def _probe(*, provider_slug: str, namespace_slug: str, fetch, seed: int) -> dict:
    return probe_frontier(
        provider_slug=provider_slug,
        namespace_slug=namespace_slug,
        fetch=fetch,
        seed=seed,
        window=settings.PROVIDER_FRONTIER_PROBE_WINDOW,
        max_misses=settings.PROVIDER_FRONTIER_MAX_MISSES,
    )


def _seed(*, provider_slug: str, namespace_slug: str, floor: int = 0) -> int:
    """Start the walk above the ids already stored, never below them."""
    return max(
        floor,
        highest_stored_id(provider_slug=provider_slug, namespace_slug=namespace_slug),
    )


@shared_task(soft_time_limit=1800, time_limit=1900)
def probe_provider_frontiers_task(job_id: str | None = None) -> dict:
    lease_owner = f"celery:{current_task.request.id}"
    if job_id and not sync_job_service.claim(
        job_id=job_id,
        lease_owner=lease_owner,
        lease_seconds=1900,
    ):
        return {"skipped": True, "reason": "job already claimed"}
    sync_job_service.mark_running(
        job_id=job_id,
        total_count=2,
        current_label="Probing provider frontiers",
        lease_owner=lease_owner,
    )
    try:
        results = [
            _probe(
                provider_slug=MAL_SOURCE.slug,
                namespace_slug=MAL_ANIME_NAMESPACE.slug,
                fetch=mal_api_client.fetch_anime,
                seed=_seed(
                    provider_slug=MAL_SOURCE.slug,
                    namespace_slug=MAL_ANIME_NAMESPACE.slug,
                    floor=int(settings.MAL_MAX_ANIME_ID),
                ),
            ),
            _probe(
                provider_slug=BANGUMI_SOURCE.slug,
                namespace_slug=BANGUMI_SUBJECT_NAMESPACE.slug,
                fetch=bangumi_client.fetch_subject,
                seed=_seed(
                    provider_slug=BANGUMI_SOURCE.slug,
                    namespace_slug=BANGUMI_SUBJECT_NAMESPACE.slug,
                ),
            ),
        ]
        result = {"frontiers": results}
        sync_job_service.mark_succeeded(
            job_id=job_id,
            result=result,
            current_label="Provider frontiers probed",
            lease_owner=lease_owner,
        )
        return result
    except Exception as exc:
        sync_job_service.mark_failed(job_id=job_id, error=exc, lease_owner=lease_owner)
        raise
