"""MAL anime client backed by the official MyAnimeList API v2.

The provider slug and namespaces identify MyAnimeList records (``mal_id``).
The transport talks directly to ``api.myanimelist.net/v2`` using the public
client authentication header (``X-MAL-CLIENT-ID``). No OAuth token is needed
for the anime detail, seasonal listing, or search endpoints this project uses;
the client secret is kept only for future OAuth-based user-scope features.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from django.conf import settings

from apps.index.models import Provider, ProviderNamespace
from apps.sync.providers.contracts import (
    CatalogSourceSpec,
    SourceNamespaceSpec,
)
from apps.sync.providers.exceptions import MALAPIError
from apps.sync.providers.rate_limiter import DistributedRateLimiter
from shared.outbound import httpx_client_kwargs

MAL_SOURCE = CatalogSourceSpec(
    slug="mal",
    name="MyAnimeList",
    base_url="https://myanimelist.net",
    terms_url="https://myanimelist.net/about/terms_of_use",
    attribution_url="https://myanimelist.net",
)
MAL_ANIME_NAMESPACE = SourceNamespaceSpec(
    source=MAL_SOURCE,
    slug="anime",
    resource_type=ProviderNamespace.ResourceType.SUBJECT,
    description="MyAnimeList anime entry",
)
MAL_SCHEDULE_ITEM_NAMESPACE = SourceNamespaceSpec(
    source=MAL_SOURCE,
    slug="schedule-item",
    resource_type=ProviderNamespace.ResourceType.SUBJECT,
    description=("MyAnimeList anime entry as seen in an official seasonal listing"),
)
MAL_SEASON_NAMESPACE = SourceNamespaceSpec(
    source=MAL_SOURCE,
    slug="season",
    resource_type=ProviderNamespace.ResourceType.SCHEDULE,
    description="Point-in-time MyAnimeList seasonal listing",
)

# Fields requested from anime detail, seasonal, and search endpoints. They cover
# everything the importer and board projection need without pulling expensive
# recommendation or related-entry trees.
MAL_ANIME_FIELDS = (
    "id,title,main_picture,alternative_titles,start_date,end_date,synopsis,"
    "mean,rank,popularity,num_list_users,num_scoring_users,nsfw,media_type,"
    "status,num_episodes,start_season,broadcast,source,"
    "average_episode_duration,rating,pictures,studios"
)

# Calendar quarters align with MAL broadcast seasons: Q1 = winter, Q2 = spring,
# Q3 = summer, Q4 = fall.
MAL_SEASON_BY_QUARTER = {
    1: "winter",
    2: "spring",
    3: "summer",
    4: "fall",
}


class MALAPIClient:
    """Small typed client for the official MAL v2 REST endpoints."""

    SEASON_MAX_LIMIT = 500
    SEARCH_MAX_LIMIT = 100
    RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
    MAX_ATTEMPTS = 3

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._rate_limiter = DistributedRateLimiter(
            "mal",
            settings.MAL_RATE_LIMIT_INTERVAL,
            allow_fallback=client is not None,
        )

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            client_id = settings.MAL_API_CLIENT_ID
            if not client_id:
                raise MALAPIError(
                    "MAL_API_CLIENT_ID is not configured. Register a MAL API "
                    "client at https://myanimelist.net/apiconfig and set the "
                    "environment variable before enabling MAL sync."
                )
            self._client = httpx.Client(
                **httpx_client_kwargs(
                    base_url=settings.MAL_API_BASE_URL,
                    headers={
                        "Accept": "application/json",
                        "X-MAL-CLIENT-ID": client_id,
                        "User-Agent": settings.MAL_USER_AGENT,
                    },
                    timeout=settings.MAL_TIMEOUT,
                    follow_redirects=True,
                    use_proxy=False,
                )
            )
        return self._client

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        provider = (
            Provider.objects.filter(slug=MAL_SOURCE.slug)
            .only("is_enabled", "storage_policy")
            .first()
        )
        if provider is not None:
            if not provider.is_enabled:
                raise MALAPIError("MAL provider is disabled.")
            if provider.storage_policy == Provider.UsagePolicy.FORBIDDEN:
                raise MALAPIError("MAL provider forbids source payload storage.")
        last_error: MALAPIError | None = None
        for attempt in range(self.MAX_ATTEMPTS):
            self._rate_limiter.acquire()
            try:
                response = self.client.get(path, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                retry_after = _retry_after(exc.response)
                error = MALAPIError(
                    f"MAL API returned {status_code}: {exc.response.text[:500]}",
                    status_code=status_code,
                    retry_after=retry_after,
                )
                if (
                    status_code in self.RETRYABLE_STATUSES
                    and attempt < self.MAX_ATTEMPTS - 1
                ):
                    last_error = error
                    delay = min(
                        90.0,
                        retry_after or (10.0 if status_code >= 500 else 5.0),
                    )
                    time.sleep(delay)
                    continue
                raise error from exc
            except httpx.RequestError as exc:
                raise MALAPIError(f"MAL API request failed: {exc}") from exc
            try:
                return response.json()
            except ValueError as exc:
                raise MALAPIError("MAL API returned invalid JSON.") from exc
        if last_error is not None:
            raise last_error
        raise MALAPIError("MAL request exhausted its retry budget.")

    def fetch_anime(self, mal_id: int) -> dict[str, Any]:
        """Return the official v2 anime record for one MAL anime."""
        payload = self._get(
            f"/anime/{mal_id}",
            {"fields": MAL_ANIME_FIELDS},
        )
        if not isinstance(payload, dict):
            raise MALAPIError(f"MAL anime {mal_id} was not found.")
        return payload

    def fetch_anime_full(self, mal_id: int) -> dict[str, Any]:
        """Backwards-compatible full-detail fetch (same as ``fetch_anime``)."""
        return self.fetch_anime(mal_id)

    def fetch_season(
        self,
        *,
        year: int,
        season: str,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Return one page of the official seasonal anime listing."""
        bounded_limit = min(max(int(limit), 1), self.SEASON_MAX_LIMIT)
        bounded_offset = max(0, int(offset))
        payload = self._get(
            f"/anime/season/{int(year)}/{season}",
            {
                "limit": bounded_limit,
                "offset": bounded_offset,
                "fields": MAL_ANIME_FIELDS,
                "nsfw": "true",
            },
        )
        if not isinstance(payload, dict):
            raise MALAPIError("MAL seasonal listing response must be an object.")
        return payload

    def search_anime(
        self,
        *,
        query: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search anime through the official v2 endpoint."""
        bounded_limit = min(max(int(limit), 1), self.SEARCH_MAX_LIMIT)
        payload = self._get(
            "/anime",
            {
                "q": query,
                "limit": bounded_limit,
                "offset": max(0, int(offset)),
                "fields": MAL_ANIME_FIELDS,
                "nsfw": "true",
            },
        )
        if not isinstance(payload, dict):
            raise MALAPIError("MAL search response must be an object.")
        return payload

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


mal_api_client = MALAPIClient()


def season_name_for_quarter(quarter: int) -> str:
    """Map a calendar quarter (1-4) to its MAL broadcast season name."""
    season = MAL_SEASON_BY_QUARTER.get(int(quarter))
    if season is None:
        raise ValueError("MAL broadcast quarter must be between 1 and 4.")
    return season


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
