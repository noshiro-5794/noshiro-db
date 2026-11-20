"""The AniList client: one GraphQL endpoint, and an error channel that is not HTTP.

GraphQL answers 200 with an ``errors`` array, so a status check is not enough. The rules
carried over from the Django client:

* ``RATE_LIMITED`` / ``INTERNAL_SERVER_ERROR`` are retryable, with backoff;
* a "temporarily disabled" message means the provider is in maintenance: it is reported as
  a 403 with a long back-off rather than retried immediately;
* anything else is a terminal error for this request.

A ``null`` media means the record is gone, which is a terminal answer, not a failure.
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any

import httpx

from api.integrations.providers.catalog import CatalogPage, DeltaPage
from api.integrations.providers.errors import ProviderError
from api.integrations.providers.http import client as build_client

CHARACTER_FIELDS = """
    edges {
      role
      node { id name { full native } image { large medium } }
      voiceActors { id name { full native } languageV2 image { large medium } }
    }
"""
STAFF_FIELDS = """
    edges { role node { id name { full native } languageV2 image { large medium } } }
"""
AIRING_FIELDS = """
    nodes { id episode airingAt timeUntilAiring }
"""
CONNECTION_FIELDS = {
    "characters": ("edges", CHARACTER_FIELDS, 25),
    "staff": ("edges", STAFF_FIELDS, 25),
    "airingSchedule": ("nodes", AIRING_FIELDS, 50),
}

MEDIA_QUERY = f"""
query ($id: Int) {{
  Media(id: $id, type: ANIME) {{
    id idMal type format status description season seasonYear episodes duration source
    averageScore popularity favourites trending isAdult genres synonyms
    bannerImage siteUrl updatedAt
    coverImage {{ extraLarge large medium color }}
    title {{ romaji english native userPreferred }}
    startDate {{ year month day }}
    endDate {{ year month day }}
    nextAiringEpisode {{ airingAt timeUntilAiring episode }}
    externalLinks {{ id url site type }}
    studios {{ edges {{ isMain node {{ id name }} }} }}
    relations {{ edges {{
      relationType node {{ id type format title {{ romaji english native }} }}
    }} }}
    tags {{ id name rank category isMediaSpoiler }}
    characters(page: 1, perPage: 25) {{ pageInfo {{ hasNextPage }} {CHARACTER_FIELDS} }}
    staff(page: 1, perPage: 25) {{ pageInfo {{ hasNextPage }} {STAFF_FIELDS} }}
    airingSchedule(page: 1, perPage: 50) {{ pageInfo {{ hasNextPage }} {AIRING_FIELDS} }}
  }}
}}
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

RETRYABLE_CODES = frozenset({"RATE_LIMITED", "INTERNAL_SERVER_ERROR"})
MAX_ATTEMPTS = 3


class AniListClient:
    def __init__(
        self,
        *,
        base_url: str = "https://graphql.anilist.co",
        user_agent: str = "noshiro-db",
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        http: httpx.Client | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self._base_url = base_url
        self._user_agent = user_agent
        self._timeout = timeout
        self._transport = transport
        self._http = http
        self._sleep = sleep
        self._storage_forbidden = False

    def forbid_storage(self, *, forbidden: bool = True) -> None:
        self._storage_forbidden = forbidden

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = build_client(
                base_url=self._base_url,
                headers={
                    "User-Agent": self._user_agent,
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
                transport=self._transport,
            )
        return self._http

    def query(self, graphql: str, variables: dict[str, Any]) -> dict[str, Any]:
        if self._storage_forbidden:
            raise ProviderError("AniList provider forbids source payload storage.")
        last_error: ProviderError | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self.http.post("", json={"query": graphql, "variables": variables})
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as error:
                status = error.response.status_code
                provider_error = ProviderError(
                    f"AniList returned {status}: {error.response.text[:500]}",
                    status_code=status,
                    retry_after=_retry_after(error.response),
                    error_code="not_found" if status == 404 else "http_error",
                )
                if (status == 429 or status >= 500) and attempt < MAX_ATTEMPTS - 1:
                    last_error = provider_error
                    self._sleep(min(30.0, 5.0 * (2**attempt)))
                    continue
                raise provider_error from error
            except httpx.RequestError as error:
                provider_error = ProviderError(
                    f"AniList request failed: {error}", error_code="transport_error"
                )
                if attempt < MAX_ATTEMPTS - 1:
                    last_error = provider_error
                    self._sleep(min(10.0, 1.5 * (2**attempt)))
                    continue
                raise provider_error from error
            except ValueError as error:
                raise ProviderError(
                    "AniList returned invalid JSON.", error_code="invalid_json"
                ) from error

            # GraphQL reports failure with HTTP 200 and ``data: null``, so the error
            # channel has to be read before the payload is judged.
            if not isinstance(payload, dict):
                raise ProviderError("AniList returned an invalid GraphQL response.")
            errors = payload.get("errors")
            if errors:
                provider_error, retryable = _graphql_error(errors)
                if retryable and attempt < MAX_ATTEMPTS - 1:
                    last_error = provider_error
                    self._sleep(min(30.0, 5.0 * (2**attempt)))
                    continue
                raise provider_error
            if not isinstance(payload.get("data"), dict):
                raise ProviderError("AniList returned an invalid GraphQL response.")
            data: dict[str, Any] = payload["data"]
            return data
        if last_error is not None:
            raise last_error
        raise ProviderError("AniList request exhausted its retry budget.")

    def fetch_media(self, anilist_id: int) -> dict[str, Any]:
        data = self.query(MEDIA_QUERY, {"id": int(anilist_id)})
        media = data.get("Media")
        if not isinstance(media, dict):
            raise ProviderError(
                f"AniList media {anilist_id} was not found.",
                status_code=404,
                error_code="not_found",
            )
        result: dict[str, Any] = media
        for connection, (items_key, fields, page_size) in CONNECTION_FIELDS.items():
            self._collect_connection(result, connection, items_key, fields, page_size)
        return result

    def _collect_connection(
        self, media: dict[str, Any], connection: str, items_key: str, fields: str, page_size: int
    ) -> None:
        current = media.get(connection)
        if not isinstance(current, dict):
            return
        page = 1
        while (current.get("pageInfo") or {}).get("hasNextPage"):
            page += 1
            query = f"""
            query ($id: Int, $page: Int, $perPage: Int) {{
              Media(id: $id, type: ANIME) {{
                id
                {connection}(page: $page, perPage: $perPage) {{
                  pageInfo {{ hasNextPage }}
                  {fields}
                }}
              }}
            }}
            """
            data = self.query(query, {"id": media["id"], "page": page, "perPage": page_size})
            next_media = data.get("Media")
            if not isinstance(next_media, dict) or next_media.get("id") != media["id"]:
                raise ProviderError("AniList connection response changed media identity.")
            current = next_media.get(connection)
            if not isinstance(current, dict) or not isinstance(current.get(items_key), list):
                raise ProviderError(f"AniList returned an invalid {connection} page.")
            if not current[items_key] and (current.get("pageInfo") or {}).get("hasNextPage"):
                raise ProviderError(f"AniList returned an empty nonterminal {connection} page.")
            media[connection].setdefault(items_key, []).extend(current[items_key])
            media[connection]["pageInfo"] = current.get("pageInfo") or {}

    DELTA_START_WATERMARK = 19400101

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

    def fetch_airing_page(
        self, *, cursor: str | None = None, page_size: int = 50
    ) -> dict[str, Any]:
        data = self.query(
            AIRING_QUERY,
            {"page": max(1, int(cursor or "1")), "perPage": min(max(page_size, 1), 50)},
        )
        page = data.get("Page")
        if not isinstance(page, dict):
            raise ProviderError("AniList returned an invalid airing page.")
        return page

    def fetch_season_page(
        self,
        *,
        season: str,
        season_year: int,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        data = self.query(
            SEASON_QUERY,
            {
                "page": max(1, int(cursor or "1")),
                "perPage": min(max(page_size, 1), 50),
                "season": season.upper(),
                "seasonYear": season_year,
            },
        )
        page = data.get("Page")
        if not isinstance(page, dict):
            raise ProviderError("AniList returned an invalid season page.")
        return page

    def discover_anime_page(self, *, cursor: str | None = None, page_size: int = 50) -> CatalogPage:
        """Discover AniList anime IDs using the provider's cursor-like page API."""
        page = max(1, int(cursor or "1"))
        data = self.query(self.CATALOG_QUERY, {"page": page, "perPage": min(max(page_size, 1), 50)})
        page_data = data.get("Page")
        if not isinstance(page_data, dict):
            raise ProviderError("AniList returned an invalid catalog page.")
        external_ids = tuple(
            str(item["id"])
            for item in page_data.get("media") or []
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        )
        page_info = page_data.get("pageInfo") or {}
        return CatalogPage(
            external_ids=external_ids,
            next_cursor=str(page + 1) if page_info.get("hasNextPage") else None,
            total_count=int(page_info["total"])
            if isinstance(page_info.get("total"), int)
            else None,
        )

    def discover_anime_delta_page(
        self, *, watermark: str, cursor: str | None = None, page_size: int = 50
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
            raise ProviderError(
                "AniList delta watermark must be a FuzzyDateInt (YYYYMMDD)."
            ) from exc
        if started_after <= 0:
            started_after = self.DELTA_START_WATERMARK
        page = max(1, int(cursor or "1"))
        data = self.query(
            self.DELTA_QUERY,
            {"page": page, "perPage": min(max(page_size, 1), 50), "startedAfter": started_after},
        )
        page_data = data.get("Page")
        if not isinstance(page_data, dict):
            raise ProviderError("AniList returned an invalid delta page.")
        items = page_data.get("media") or []
        external_ids = tuple(
            str(item["id"])
            for item in items
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        )
        page_watermark = max(
            (self._fuzzy_date(item.get("startDate")) for item in items if isinstance(item, dict)),
            default=started_after,
        )
        page_info = page_data.get("pageInfo") or {}
        return DeltaPage(
            external_ids=external_ids,
            next_cursor=str(page + 1) if page_info.get("hasNextPage") else None,
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
        month_value = value.get("month")
        day_value = value.get("day")
        month = month_value if isinstance(month_value, int) else 0
        day = day_value if isinstance(day_value, int) else 0
        return year * 10000 + month * 100 + day

    @staticmethod
    def _previous_day(fuzzy_date: int) -> int:
        if fuzzy_date <= 0:
            return 0
        (year, remainder) = divmod(fuzzy_date, 10000)
        (month, day) = divmod(remainder, 100)
        if not month or not day:
            return fuzzy_date
        try:
            previous = date(year, month, day) - timedelta(days=1)
        except ValueError:
            return fuzzy_date
        return previous.year * 10000 + previous.month * 100 + previous.day

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None


def _graphql_error(errors: Any) -> tuple[ProviderError, bool]:
    """Translate a GraphQL ``errors`` array into one error and whether to retry it."""
    first = errors[0] if isinstance(errors, list) and errors else errors
    detail = str(first)[:500]
    if "temporarily disabled" in detail.lower():
        return (
            ProviderError(
                f"AniList GraphQL error: {detail}",
                status_code=403,
                retry_after=900,
                error_code="provider_maintenance",
            ),
            False,
        )
    codes = {
        error["extensions"].get("code")
        for error in (errors if isinstance(errors, list) else [errors])
        if isinstance(error, dict) and isinstance(error.get("extensions"), dict)
    }
    retryable = bool(codes & RETRYABLE_CODES)
    status = 429 if "RATE_LIMITED" in codes else (503 if retryable else None)
    return ProviderError(f"AniList GraphQL error: {detail}", status_code=status), retryable


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


__all__ = ["MEDIA_QUERY", "AniListClient"]
