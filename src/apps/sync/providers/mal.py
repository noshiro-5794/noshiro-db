"""MAL anime client backed by the public Jikan REST API.

The provider slug and namespaces identify MyAnimeList records (``mal_id``);
the transport simply calls Jikan, which is an unofficial, key-less HTTP
interface to MAL data. No official MAL credentials are needed for the daily
schedule workflows this provider powers.
"""

from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings

from apps.index.models import Provider, ProviderNamespace
from apps.sync.providers.contracts import (
    CatalogPage,
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
    description="MyAnimeList anime entry as seen in a weekly schedule page",
)
MAL_SCHEDULE_NAMESPACE = SourceNamespaceSpec(
    source=MAL_SOURCE,
    slug="schedule",
    resource_type=ProviderNamespace.ResourceType.SCHEDULE,
    description="Jikan weekly broadcast schedule page",
)
MAL_SEASON_NAMESPACE = SourceNamespaceSpec(
    source=MAL_SOURCE,
    slug="season",
    resource_type=ProviderNamespace.ResourceType.SCHEDULE,
    description="Jikan seasonal anime listing",
)

JIKAN_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "other",
    "unknown",
)


class JikanClient:
    """Small typed client for the Jikan v4 REST endpoints used by the board."""

    MAX_PAGE_SIZE = 25

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._rate_limiter = DistributedRateLimiter(
            "mal",
            settings.JIKAN_RATE_LIMIT_INTERVAL,
            allow_fallback=client is not None,
        )

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                **httpx_client_kwargs(
                    base_url=settings.JIKAN_API_BASE_URL,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": settings.JIKAN_USER_AGENT,
                    },
                    timeout=settings.JIKAN_TIMEOUT,
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
        self._rate_limiter.acquire()
        try:
            response = self.client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise MALAPIError(
                f"Jikan API returned {exc.response.status_code}: "
                f"{exc.response.text[:500]}",
                status_code=exc.response.status_code,
                retry_after=_retry_after(exc.response),
            ) from exc
        except httpx.RequestError as exc:
            raise MALAPIError(f"Jikan API request failed: {exc}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise MALAPIError("Jikan API returned invalid JSON.") from exc

    def fetch_anime(self, mal_id: int) -> dict[str, Any]:
        """Return the compact ``/anime/{id}`` record for one MAL anime."""
        payload = self._get(f"/anime/{mal_id}")
        item = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(item, dict):
            raise MALAPIError(f"MAL anime {mal_id} was not found.")
        return item

    def fetch_anime_full(self, mal_id: int) -> dict[str, Any]:
        """Return the extended ``/anime/{id}/full`` record when details are needed."""
        payload = self._get(f"/anime/{mal_id}/full")
        item = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(item, dict):
            raise MALAPIError(f"MAL anime {mal_id} was not found.")
        return item

    def fetch_season_now(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 25,
    ) -> dict[str, Any]:
        page = max(1, int(cursor or "1"))
        return self._get(
            "/seasons/now",
            {
                "page": page,
                "limit": self._bounded_page_size(page_size),
            },
        )

    def fetch_schedule(
        self,
        *,
        weekday: str,
        cursor: str | None = None,
        page_size: int = 25,
    ) -> dict[str, Any]:
        if weekday not in JIKAN_WEEKDAYS:
            raise ValueError(
                f"Jikan weekday must be one of {', '.join(JIKAN_WEEKDAYS)}."
            )
        page = max(1, int(cursor or "1"))
        return self._get(
            "/schedules",
            {
                "filter": weekday,
                "page": page,
                "limit": self._bounded_page_size(page_size),
            },
        )

    def discover_season_now_page(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 25,
    ) -> CatalogPage:
        """Discover MAL ids in the current anime season with Jikan pagination."""
        payload = self.fetch_season_now(cursor=cursor, page_size=page_size)
        return self._catalog_page(payload, cursor=cursor)

    def discover_schedule_page(
        self,
        *,
        weekday: str,
        cursor: str | None = None,
        page_size: int = 25,
    ) -> CatalogPage:
        """Discover MAL ids that broadcast on one weekday."""
        payload = self.fetch_schedule(
            weekday=weekday,
            cursor=cursor,
            page_size=page_size,
        )
        return self._catalog_page(payload, cursor=cursor)

    def _catalog_page(self, payload: Any, *, cursor: str | None) -> CatalogPage:
        if not isinstance(payload, dict):
            raise MALAPIError("Jikan catalog response must be an object.")
        items = payload.get("data")
        if not isinstance(items, list):
            raise MALAPIError("Jikan catalog response is missing its data list.")
        external_ids = tuple(
            str(item["mal_id"])
            for item in items
            if isinstance(item, dict) and isinstance(item.get("mal_id"), int)
        )
        pagination = payload.get("pagination") if isinstance(payload, dict) else {}
        has_next = (
            isinstance(pagination, dict) and pagination.get("has_next_page") is True
        )
        page = max(1, int(cursor or "1"))
        return CatalogPage(
            external_ids=external_ids,
            next_cursor=str(page + 1) if has_next else None,
            total_count=None,
        )

    @classmethod
    def _bounded_page_size(cls, page_size: int) -> int:
        return min(max(int(page_size), 1), cls.MAX_PAGE_SIZE)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


jikan_client = JikanClient()


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
