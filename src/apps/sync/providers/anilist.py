import time
from datetime import date, timedelta
from typing import Any

import httpx
from django.conf import settings

from apps.index.models import Provider, ProviderNamespace
from apps.sync.providers.contracts import (
    CatalogPage,
    CatalogSourceSpec,
    DeltaPage,
    SourceNamespaceSpec,
)
from apps.sync.providers.exceptions import AniListAPIError
from apps.sync.providers.rate_limiter import DistributedRateLimiter
from shared.outbound import httpx_client_kwargs

ANILIST_SOURCE = CatalogSourceSpec(
    slug="anilist",
    name="AniList",
    base_url="https://anilist.co",
    terms_url="https://anilist.gitbook.io/anilist-apiv2-docs/",
    attribution_url="https://anilist.co",
)
ANILIST_ANIME_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="anime",
    resource_type=ProviderNamespace.ResourceType.SUBJECT,
    description="AniList anime media",
)
ANILIST_EPISODE_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="episode",
    resource_type=ProviderNamespace.ResourceType.EPISODE,
    description="AniList airing schedule episode",
)
ANILIST_CALENDAR_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="calendar",
    resource_type=ProviderNamespace.ResourceType.SCHEDULE,
    description="Point-in-time AniList airing schedule for a media entry",
)
ANILIST_SEASON_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="season",
    resource_type=ProviderNamespace.ResourceType.SCHEDULE,
    description="Point-in-time AniList seasonal anime listing",
)
ANILIST_SEASON_ITEM_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="season-item",
    resource_type=ProviderNamespace.ResourceType.SUBJECT,
    description="AniList anime entry as seen in a seasonal listing",
)
ANILIST_CHARACTER_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="character",
    resource_type=ProviderNamespace.ResourceType.CHARACTER,
    description="AniList character",
)
ANILIST_STAFF_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="staff",
    resource_type=ProviderNamespace.ResourceType.PERSON,
    description="AniList staff person",
)
ANILIST_STUDIO_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="studio",
    resource_type=ProviderNamespace.ResourceType.ORGANIZATION,
    description="AniList animation studio",
)
ANILIST_GENRE_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="genre",
    resource_type=ProviderNamespace.ResourceType.TAXONOMY,
    description="AniList genre",
)
ANILIST_TAG_NAMESPACE = SourceNamespaceSpec(
    source=ANILIST_SOURCE,
    slug="tag",
    resource_type=ProviderNamespace.ResourceType.TAXONOMY,
    description="AniList media tag",
)


class AniListClient:
    # First air date the catalogue walk starts from (FuzzyDateInt).
    DELTA_START_WATERMARK = 19400101
    MAX_ATTEMPTS = 3

    CATALOG_QUERY = """
    query ($page: Int!, $perPage: Int!) {
      Page(page: $page, perPage: $perPage) {
        pageInfo { hasNextPage total }
        media(type: ANIME, sort: ID) { id }
      }
    }
    """
    DELTA_QUERY = """
    query ($page: Int!, $perPage: Int!, $startedAfter: FuzzyDateInt!) {
      Page(page: $page, perPage: $perPage) {
        pageInfo { hasNextPage }
        media(type: ANIME, sort: START_DATE, startDate_greater: $startedAfter) {
          id
          startDate { year month day }
        }
      }
    }
    """
    SEASON_QUERY = """
    query ($page: Int!, $perPage: Int!, $season: MediaSeason, $seasonYear: Int!) {
      Page(page: $page, perPage: $perPage) {
        pageInfo { hasNextPage total }
        media(
          type: ANIME
          season: $season
          seasonYear: $seasonYear
          status_in: [RELEASING]
          sort: [ID]
        ) {
          id
          idMal
          type
          format
          status
          season
          seasonYear
          episodes
          duration
          isAdult
          siteUrl
          startDate { year month day }
          endDate { year month day }
          nextAiringEpisode { airingAt episode }
          title { romaji english native userPreferred }
          coverImage { extraLarge large medium color }
          airingSchedule(notYetAired: true, perPage: 50) {
            nodes { id episode airingAt timeUntilAiring }
          }
        }
      }
    }
    """
    AIRING_QUERY = """
    query ($page: Int!, $perPage: Int!) {
      Page(page: $page, perPage: $perPage) {
        pageInfo { hasNextPage total }
        media(type: ANIME, status_in: [RELEASING, NOT_YET_RELEASED], sort: [ID]) {
          id
          idMal
          type
          format
          status
          season
          seasonYear
          episodes
          duration
          isAdult
          siteUrl
          startDate { year month day }
          endDate { year month day }
          nextAiringEpisode { airingAt episode }
          title { romaji english native userPreferred }
          coverImage { extraLarge large medium color }
          airingSchedule(notYetAired: true, perPage: 50) {
            nodes { id episode airingAt timeUntilAiring }
          }
        }
      }
    }
    """
    MEDIA_QUERY = """
    query ($id: Int, $page: Int, $perPage: Int) {
      Media(id: $id, type: ANIME) {
        id
        idMal
        type
        format
        status
        description
        season
        seasonYear
        episodes
        duration
        source
        averageScore
        popularity
        favourites
        trending
        isAdult
        genres
        synonyms
        coverImage { extraLarge large medium color }
        bannerImage
        siteUrl
        updatedAt
        title { romaji english native userPreferred }
        startDate { year month day }
        endDate { year month day }
        nextAiringEpisode { airingAt timeUntilAiring episode }
        externalLinks { id url site type }
        studios { edges { isMain node { id name } } }
        staff { edges { role node { id name { full native } languageV2 image { large medium } } } }
        characters { edges { role node { id name { full native } image { large medium } } voiceActors { id name { full native } languageV2 image { large medium } } } }
        relations { edges { relationType node { id type title { romaji english native } } } }
        tags { id name rank category isMediaSpoiler }
        airingSchedule(page: $page, perPage: $perPage) {
          pageInfo { hasNextPage }
          nodes { id episode airingAt timeUntilAiring }
        }
      }
    }
    """

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._rate_limiter = DistributedRateLimiter(
            "anilist",
            settings.ANILIST_RATE_LIMIT_INTERVAL,
            allow_fallback=client is not None,
        )

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                **httpx_client_kwargs(
                    base_url=settings.ANILIST_API_BASE_URL,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": settings.ANILIST_USER_AGENT,
                    },
                    timeout=settings.ANILIST_TIMEOUT,
                    follow_redirects=True,
                    use_proxy=False,
                )
            )
        return self._client

    def _post(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        provider = (
            Provider.objects.filter(slug=ANILIST_SOURCE.slug)
            .only("is_enabled", "storage_policy")
            .first()
        )
        if provider is not None:
            if not provider.is_enabled:
                raise AniListAPIError("AniList provider is disabled.")
            if provider.storage_policy == Provider.UsagePolicy.FORBIDDEN:
                raise AniListAPIError(
                    "AniList provider forbids source payload storage."
                )

        last_error: AniListAPIError | None = None
        for attempt in range(self.MAX_ATTEMPTS):
            self._rate_limiter.acquire()
            try:
                response = self.client.post(
                    "", json={"query": query, "variables": variables}
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                response_text = exc.response.text
                retry_after = _retry_after(exc.response)
                unavailable = (
                    status_code == 403
                    and "temporarily disabled" in response_text.lower()
                )
                if unavailable:
                    # Maintenance is a server-side outage: do not hammer it.
                    raise AniListAPIError(
                        f"AniList returned HTTP {status_code}: {response_text[:500]}",
                        status_code=status_code,
                        retry_after=retry_after or 900,
                        unavailable_reason="provider_maintenance",
                    ) from exc
                error = AniListAPIError(
                    f"AniList returned HTTP {status_code}: {response_text[:500]}",
                    status_code=status_code,
                    retry_after=retry_after,
                )
                if (
                    status_code in {429, 500, 502, 503, 504}
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
                error = AniListAPIError(f"AniList request failed: {exc}")
                if attempt < self.MAX_ATTEMPTS - 1:
                    last_error = error
                    time.sleep(min(10.0, 1.5 * (2**attempt)))
                    continue
                raise error from exc
            except ValueError as exc:
                raise AniListAPIError("AniList returned invalid JSON.") from exc

            if not isinstance(payload, dict) or not isinstance(
                payload.get("data"), dict
            ):
                raise AniListAPIError("AniList returned an invalid GraphQL response.")
            if errors := payload.get("errors"):
                detail = str(errors[0] if isinstance(errors, list) else errors)[:500]
                unavailable = "temporarily disabled" in detail.lower()
                if unavailable:
                    raise AniListAPIError(
                        f"AniList GraphQL error: {detail}",
                        status_code=403,
                        retry_after=900,
                        unavailable_reason="provider_maintenance",
                    )
                retryable = any(
                    isinstance(error, dict)
                    and error.get("extensions", {}).get("code")
                    in {"RATE_LIMITED", "INTERNAL_SERVER_ERROR"}
                    for error in (errors if isinstance(errors, list) else [errors])
                )
                error = AniListAPIError(f"AniList GraphQL error: {detail}")
                error.retryable = retryable
                if retryable and attempt < self.MAX_ATTEMPTS - 1:
                    last_error = error
                    time.sleep(min(30.0, 5.0 * (2**attempt)))
                    continue
                raise error
            return payload["data"]
        if last_error is not None:
            raise last_error
        raise AniListAPIError("AniList request exhausted its retry budget.")

    def fetch_media(
        self,
        anilist_id: int,
        *,
        airing_page: int = 1,
        airing_per_page: int = 50,
    ) -> dict[str, Any]:
        data = self._post(
            self.MEDIA_QUERY,
            {"id": anilist_id, "page": airing_page, "perPage": airing_per_page},
        )
        media = data.get("Media")
        if not isinstance(media, dict):
            raise AniListAPIError(f"AniList media {anilist_id} was not found.")
        return media

    def fetch_season_page(
        self,
        *,
        season: str,
        season_year: int,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        page = max(1, int(cursor or "1"))
        data = self._post(
            self.SEASON_QUERY,
            {
                "page": page,
                "perPage": min(max(page_size, 1), 50),
                "season": season.upper(),
                "seasonYear": season_year,
            },
        )
        page_data = data.get("Page")
        if not isinstance(page_data, dict):
            raise AniListAPIError("AniList returned an invalid season page.")
        return page_data

    def fetch_airing_page(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Return one page of every currently releasing anime."""
        page = max(1, int(cursor or "1"))
        data = self._post(
            self.AIRING_QUERY,
            {
                "page": page,
                "perPage": min(max(page_size, 1), 50),
            },
        )
        page_data = data.get("Page")
        if not isinstance(page_data, dict):
            raise AniListAPIError("AniList returned an invalid airing page.")
        return page_data

    def discover_anime_page(
        self, *, cursor: str | None = None, page_size: int = 50
    ) -> CatalogPage:
        """Discover AniList anime IDs using the provider's cursor-like page API."""
        page = max(1, int(cursor or "1"))
        data = self._post(
            self.CATALOG_QUERY,
            {"page": page, "perPage": min(max(page_size, 1), 50)},
        )
        page_data = data.get("Page")
        if not isinstance(page_data, dict):
            raise AniListAPIError("AniList returned an invalid catalog page.")
        external_ids = tuple(
            str(item["id"])
            for item in page_data.get("media") or []
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        )
        page_info = page_data.get("pageInfo") or {}
        return CatalogPage(
            external_ids=external_ids,
            next_cursor=str(page + 1) if page_info.get("hasNextPage") else None,
            total_count=(
                int(page_info["total"])
                if isinstance(page_info.get("total"), int)
                else None
            ),
        )

    def discover_anime_delta_page(
        self,
        *,
        watermark: str,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> DeltaPage:
        """Walk the catalogue by air date.

        AniList has no "updated since" filter and refuses page depths beyond
        5000 entries, so a crawl partitions the catalogue by ``startDate`` and
        moves the window forward as it goes. Titles with no air date are not
        reachable this way; the season and airing syncs cover those.
        """
        try:
            started_after = int(watermark)
        except (TypeError, ValueError) as exc:
            raise AniListAPIError(
                "AniList delta watermark must be a FuzzyDateInt (YYYYMMDD)."
            ) from exc
        if started_after <= 0:
            started_after = self.DELTA_START_WATERMARK
        page = max(1, int(cursor or "1"))
        data = self._post(
            self.DELTA_QUERY,
            {
                "page": page,
                "perPage": min(max(page_size, 1), 50),
                "startedAfter": started_after,
            },
        )
        page_data = data.get("Page")
        if not isinstance(page_data, dict):
            raise AniListAPIError("AniList returned an invalid delta page.")
        items = page_data.get("media") or []
        external_ids = tuple(
            str(item["id"])
            for item in items
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        )
        page_watermark = max(
            (
                self._fuzzy_date(item.get("startDate"))
                for item in items
                if isinstance(item, dict)
            ),
            default=started_after,
        )
        page_info = page_data.get("pageInfo") or {}
        return DeltaPage(
            external_ids=external_ids,
            next_cursor=str(page + 1) if page_info.get("hasNextPage") else None,
            # Step back a day so titles sharing the boundary date are re-listed
            # in the next window instead of being skipped; duplicate work items
            # are ignored on insert.
            watermark=str(max(started_after, self._previous_day(page_watermark))),
        )

    @staticmethod
    def _fuzzy_date(value: Any) -> int:
        """Render AniList's ``{year, month, day}`` as a FuzzyDateInt."""
        if not isinstance(value, dict):
            return 0
        year = value.get("year")
        if not isinstance(year, int) or year <= 0:
            return 0
        month = value.get("month") if isinstance(value.get("month"), int) else 0
        day = value.get("day") if isinstance(value.get("day"), int) else 0
        return year * 10_000 + month * 100 + day

    @staticmethod
    def _previous_day(fuzzy_date: int) -> int:
        if fuzzy_date <= 0:
            return 0
        year, remainder = divmod(fuzzy_date, 10_000)
        month, day = divmod(remainder, 100)
        if not month or not day:
            return fuzzy_date
        try:
            previous = date(year, month, day) - timedelta(days=1)
        except ValueError:
            return fuzzy_date
        return previous.year * 10_000 + previous.month * 100 + previous.day

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


anilist_client = AniListClient()


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
