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
from typing import Any

import httpx

from api.worker.providers.errors import ProviderError
from api.worker.providers.http import client as build_client

MEDIA_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    idMal
    title { romaji english native }
    description
    startDate { year month day }
    endDate { year month day }
    episodes
    duration
    format
    status
    season
    seasonYear
    averageScore
    popularity
    coverImage { large medium }
    genres
    tags { name rank }
    studios { edges { node { name } } }
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
        return result


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
    retryable = any(
        isinstance(error, dict) and error.get("extensions", {}).get("code") in RETRYABLE_CODES
        for error in (errors if isinstance(errors, list) else [errors])
    )
    return ProviderError(f"AniList GraphQL error: {detail}"), retryable


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


__all__ = ["MEDIA_QUERY", "AniListClient"]
