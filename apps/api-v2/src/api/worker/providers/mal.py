"""The MAL v2 client.

Three behaviours are carried over, because each one has a failure mode that is silent:

* The client id comes from the environment; without it the client refuses to build rather
  than sending unauthenticated requests that will be rejected later.
* Retryable statuses (429 and the 5xx family) are retried a bounded number of times, and a
  ``retry-after`` hint wins over the default back-off.
* Discovery walks the numeric id space up to the frontier the probe task proved, not up to
  a constant: a ceiling somebody has to remember to raise silently stops covering the
  newest entries.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from api.worker.providers.errors import ProviderError, retry_after_seconds

MAL_ANIME_FIELDS = (
    "id,title,main_picture,alternative_titles,start_date,end_date,synopsis,"
    "mean,rank,popularity,num_list_users,num_scoring_users,nsfw,media_type,"
    "status,num_episodes,start_season,broadcast,source,"
    "average_episode_duration,rating,studios,genres,my_list_status"
)

MAL_SEASON_BY_QUARTER = {1: "winter", 2: "spring", 3: "summer", 4: "fall"}

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 3


def season_name_for_quarter(quarter: int) -> str:
    season = MAL_SEASON_BY_QUARTER.get(int(quarter))
    if season is None:
        raise ValueError("MAL broadcast quarter must be between 1 and 4.")
    return season


class MALClient:
    SEASON_MAX_LIMIT = 500
    SEARCH_MAX_LIMIT = 100

    def __init__(
        self,
        *,
        client_id: str | None = None,
        base_url: str = "https://api.myanimelist.net/v2",
        timeout: float = 30.0,
        http: httpx.Client | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self._client_id = (
            client_id if client_id is not None else os.environ.get("MAL_API_CLIENT_ID", "")
        )
        self._base_url = base_url
        self._timeout = timeout
        self._http = http
        self._sleep = sleep
        self._storage_forbidden = False

    def forbid_storage(self, *, forbidden: bool = True) -> None:
        self._storage_forbidden = forbidden

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            if not self._client_id:
                raise ProviderError(
                    "MAL_API_CLIENT_ID is not configured. Register a MAL API client "
                    "and set the environment variable before enabling MAL sync."
                )
            from api.worker.providers.http import client as build_client

            self._http = build_client(
                base_url=self._base_url,
                headers={
                    "X-MAL-CLIENT-ID": self._client_id,
                    "User-Agent": os.environ.get("MAL_USER_AGENT", "noshiro-db"),
                },
                timeout=self._timeout,
            )
        return self._http

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if self._storage_forbidden:
            raise ProviderError("MAL provider forbids source payload storage.")
        last_error: ProviderError | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self.http.get(path, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as error:
                response = error.response
                status = response.status_code
                provider_error = ProviderError(
                    f"MAL API returned {status}: {response.text[:500]}",
                    status_code=status,
                    retry_after=retry_after_seconds(response.headers),
                    error_code="not_found" if status == 404 else "http_error",
                )
                if status in RETRYABLE_STATUSES and attempt < MAX_ATTEMPTS - 1:
                    last_error = provider_error
                    self._sleep(
                        min(90.0, provider_error.retry_after or (10.0 if status >= 500 else 5.0))
                    )
                    continue
                raise provider_error from error
            except httpx.RequestError as error:
                raise ProviderError(
                    f"MAL API request failed: {error}", error_code="transport_error"
                ) from error
            except ValueError as error:
                raise ProviderError(
                    "MAL API returned invalid JSON.", error_code="invalid_json"
                ) from error
        if last_error is not None:
            raise last_error
        raise ProviderError("MAL request exhausted its retry budget.")

    def fetch_anime(self, mal_id: int) -> dict[str, Any]:
        payload = self._get(f"/anime/{mal_id}", {"fields": MAL_ANIME_FIELDS})
        if not isinstance(payload, dict):
            raise ProviderError(f"MAL anime {mal_id} was not found.")
        return payload

    def fetch_season(
        self, *, year: int, season: str, offset: int = 0, limit: int = 100
    ) -> dict[str, Any]:
        payload = self._get(
            f"/anime/season/{int(year)}/{season}",
            {
                "limit": min(max(int(limit), 1), self.SEASON_MAX_LIMIT),
                "offset": max(0, int(offset)),
                "fields": MAL_ANIME_FIELDS,
                "nsfw": "true",
            },
        )
        if not isinstance(payload, dict):
            raise ProviderError("MAL seasonal listing response must be an object.")
        return payload

    def search_anime(self, *, query: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        payload = self._get(
            "/anime",
            {
                "q": query,
                "limit": min(max(int(limit), 1), self.SEARCH_MAX_LIMIT),
                "offset": max(0, int(offset)),
                "fields": MAL_ANIME_FIELDS,
                "nsfw": "true",
            },
        )
        if not isinstance(payload, dict):
            raise ProviderError("MAL search response must be an object.")
        return payload

    def discover_anime_page(
        self, *, ceiling: int, cursor: str | None = None, page_size: int = 100
    ) -> tuple[list[str], str | None]:
        """Ids to try, up to the proved frontier.

        MAL has no "list every anime" endpoint, so the id space itself is the
        enumeration; the importer retires the ids that answer 404, which costs one
        request each.
        """
        start = max(1, int(cursor or "1"))
        if start > ceiling:
            return [], None
        end = min(ceiling, start + max(1, int(page_size)) - 1)
        return [str(mal_id) for mal_id in range(start, end + 1)], (
            str(end + 1) if end < ceiling else None
        )


__all__ = [
    "MAL_ANIME_FIELDS",
    "MAL_SEASON_BY_QUARTER",
    "MALClient",
    "season_name_for_quarter",
]
