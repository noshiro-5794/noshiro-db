from typing import Any

import httpx
from django.conf import settings

from apps.index.models import Provider, ProviderRecord
from apps.sync.providers.contracts import (
    CatalogPage,
    CatalogSourceSpec,
    DeltaPage,
    SourceNamespaceSpec,
)
from apps.sync.providers.exceptions import BangumiAPIError
from apps.sync.providers.frontier import highest_stored_id, read_frontier
from apps.sync.providers.rate_limiter import DistributedRateLimiter
from shared.outbound import httpx_client_kwargs

BANGUMI_SOURCE = CatalogSourceSpec(
    slug="bangumi",
    name="Bangumi",
    base_url="https://bgm.tv",
    terms_url="https://bangumi.github.io/api/",
    attribution_url="https://bgm.tv",
)
BANGUMI_SUBJECT_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="subject",
    resource_type="subject",
    description="Bangumi subject",
)
BANGUMI_EPISODE_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="episode",
    resource_type="episode",
    description="Bangumi episode",
)
BANGUMI_PERSON_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="person",
    resource_type="person",
    description="Bangumi person, company, or group",
)
BANGUMI_CHARACTER_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="character",
    resource_type="character",
    description="Bangumi character",
)
BANGUMI_SUBJECT_RELATIONS_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="subject-relations",
    resource_type="collection",
    description="Point-in-time related-subject collection for a Bangumi subject",
)
BANGUMI_SUBJECT_STAFF_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="subject-staff",
    resource_type="collection",
    description="Point-in-time staff collection for a Bangumi subject",
)
BANGUMI_SUBJECT_CHARACTERS_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="subject-characters",
    resource_type="collection",
    description="Point-in-time character and voice cast collection for a subject",
)
BANGUMI_SUBJECT_EPISODES_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="subject-episodes",
    resource_type="collection",
    description="Point-in-time episode collection for a Bangumi subject",
)
BANGUMI_CALENDAR_NAMESPACE = SourceNamespaceSpec(
    source=BANGUMI_SOURCE,
    slug="calendar",
    resource_type="schedule",
    description="Point-in-time Bangumi weekly broadcast calendar",
)


class BangumiClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._rate_limiter = DistributedRateLimiter(
            "bangumi",
            settings.BANGUMI_RATE_LIMIT_INTERVAL,
            allow_fallback=client is not None,
        )

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    @staticmethod
    def _build_client() -> httpx.Client:
        headers = {
            "Accept": "application/json",
            "User-Agent": settings.BANGUMI_USER_AGENT,
        }
        if settings.BANGUMI_API_KEY:
            headers["Authorization"] = f"Bearer {settings.BANGUMI_API_KEY}"
        return httpx.Client(
            **httpx_client_kwargs(
                base_url=settings.BANGUMI_API_BASE_URL,
                headers=headers,
                timeout=settings.BANGUMI_TIMEOUT,
                follow_redirects=True,
            )
        )

    def _ensure_provider_allowed(self) -> None:
        provider = (
            Provider.objects.filter(slug=BANGUMI_SOURCE.slug)
            .only("is_enabled", "storage_policy")
            .first()
        )
        if provider is not None:
            if not provider.is_enabled:
                raise BangumiAPIError("Bangumi provider is disabled.")
            if provider.storage_policy == Provider.UsagePolicy.FORBIDDEN:
                raise BangumiAPIError(
                    "Bangumi provider forbids source payload storage."
                )

    def _get(self, path: str, **kwargs: Any) -> Any:
        self._ensure_provider_allowed()
        self._rate_limiter.acquire()
        try:
            response = self.client.get(path, **kwargs)
            self._rate_limiter.observe(response.headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise BangumiAPIError(
                f"Bangumi API returned {exc.response.status_code}: {detail}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise BangumiAPIError(f"Bangumi API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise BangumiAPIError("Bangumi API returned invalid JSON.") from exc

    def _post(self, path: str, **kwargs: Any) -> Any:
        self._ensure_provider_allowed()
        self._rate_limiter.acquire()
        try:
            response = self.client.post(path, **kwargs)
            self._rate_limiter.observe(response.headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise BangumiAPIError(
                f"Bangumi API returned {exc.response.status_code}: {detail}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise BangumiAPIError(f"Bangumi API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise BangumiAPIError("Bangumi API returned invalid JSON.") from exc

    def fetch_calendar(self) -> list[dict[str, Any]]:
        return self._get("/calendar")

    def fetch_subject(self, subject_id: int) -> dict[str, Any]:
        return self._get(f"/v0/subjects/{subject_id}")

    def search_subjects(
        self,
        *,
        keyword: str,
        subject_types: tuple[int, ...] = (2,),
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search subjects through the experimental v0 search endpoint.

        The endpoint filters anime (type 2) by default so external search can
        be reused safely by the AI harness without returning books/games/etc.
        """
        normalized = keyword.strip()
        if not normalized:
            raise ValueError("Bangumi subject search requires a keyword.")
        params = {
            "limit": min(max(int(limit), 1), 50),
            "offset": max(0, int(offset)),
        }
        body: dict[str, Any] = {
            "keyword": normalized[:512],
            "sort": "match",
        }
        if subject_types:
            body["filter"] = {"type": [int(value) for value in subject_types]}
        payload = self._post("/v0/search/subjects", params=params, json=body)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise BangumiAPIError(
                "Bangumi subject search response must contain a data list."
            )
        return payload

    def discover_subject_page(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 100,
    ) -> CatalogPage:
        """Enumerate subject ids by walking the id space.

        ``GET /v0/subjects`` is a bounded browse view - the API rejects offsets
        past its own ceiling, and the view is approximate rather than a stable
        enumeration - so it cannot be the basis of a full sync that claims
        completeness. Subject ids are handed out monotonically and the space is
        99.7% occupied, so walking it costs one request per gap and proves what
        it covered: every id either answered or retired as non-existent.

        The walk stops at the frontier the probe proved rather than at a
        constant, and the importer retires the ids that answer 404.
        """
        ceiling = read_frontier(
            provider_slug=BANGUMI_SOURCE.slug,
            namespace_slug=BANGUMI_SUBJECT_NAMESPACE.slug,
            seed=highest_stored_id(
                provider_slug=BANGUMI_SOURCE.slug,
                namespace_slug=BANGUMI_SUBJECT_NAMESPACE.slug,
            ),
        ).ceiling
        start = max(1, int(cursor or "1"))
        if start > ceiling:
            return CatalogPage(external_ids=(), next_cursor=None, total_count=ceiling)
        end = min(ceiling, start + max(1, int(page_size)) - 1)
        return CatalogPage(
            external_ids=tuple(str(subject_id) for subject_id in range(start, end + 1)),
            next_cursor=str(end + 1) if end < ceiling else None,
            total_count=ceiling,
        )

    def discover_subject_delta_page(
        self,
        *,
        watermark: str,
        cursor: str | None = None,
        page_size: int = 100,
    ) -> DeltaPage:
        """Re-fetch known records so upstream edits land.

        Bangumi publishes no change feed — every ``/v0/revisions/*`` endpoint
        asks for one entity — so an edit can only be found by asking again. New
        ids are a separate concern: the frontier probe extends the space and the
        incremental walk covers it.
        """
        del watermark
        offset = max(0, int(cursor or "0"))
        limit = min(max(page_size, 1), 1000)
        records = ProviderRecord.objects.filter(
            namespace__provider__slug=BANGUMI_SOURCE.slug,
            namespace__slug=BANGUMI_SUBJECT_NAMESPACE.slug,
            status=ProviderRecord.Status.ACTIVE,
        ).order_by("external_id")
        external_ids = tuple(
            records.values_list("external_id", flat=True)[offset : offset + limit]
        )
        return DeltaPage(
            external_ids=external_ids,
            next_cursor=str(offset + limit) if len(external_ids) == limit else None,
            watermark="known-record-reconciliation",
            total_count=records.count(),
        )

    def fetch_subject_persons(self, subject_id: int) -> list[dict[str, Any]]:
        return self._get(f"/v0/subjects/{subject_id}/persons")

    def fetch_subject_characters(self, subject_id: int) -> list[dict[str, Any]]:
        return self._get(f"/v0/subjects/{subject_id}/characters")

    def fetch_subject_subjects(self, subject_id: int) -> list[dict[str, Any]]:
        return self._get(f"/v0/subjects/{subject_id}/subjects")

    def fetch_subject_episodes(
        self,
        subject_id: int,
        episode_type: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        params = {"subject_id": subject_id, "limit": limit, "offset": offset}
        if episode_type is not None:
            params["type"] = episode_type
        return self._get("/v0/episodes", params=params)

    def fetch_character(self, character_id: int) -> dict[str, Any]:
        return self._get(f"/v0/characters/{character_id}")

    def fetch_person(self, person_id: int) -> dict[str, Any]:
        return self._get(f"/v0/persons/{person_id}")

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


bangumi_client = BangumiClient()
