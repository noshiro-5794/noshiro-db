"""The Bangumi client: a JSON API that speaks `/calendar` and `/v0/subjects/{id}`.

Two behaviours carried over from the Django client:

* the API key is optional — Bangumi serves these endpoints anonymously, but an
  authenticated request is used when ``BANGUMI_API_KEY`` is set;
* a provider row that forbids payload storage blocks the request before it is sent.

The transport (proxy, error classification, absolute-URL refusal) is shared, so this file
only describes the endpoints and the shapes they answer with.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from api.integrations.providers.errors import ProviderError
from api.integrations.providers.http import client as build_client
from api.integrations.providers.http import send


class BangumiClient:
    def __init__(
        self,
        *,
        base_url: str = "https://api.bgm.tv",
        api_key: str | None = None,
        user_agent: str = "noshiro-db",
        timeout: float = 30.0,
        http: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key if api_key is not None else os.environ.get("BANGUMI_API_KEY", "")
        self._user_agent = user_agent
        self._timeout = timeout
        self._http = http
        self._transport = transport
        self._storage_forbidden = False

    def forbid_storage(self, *, forbidden: bool = True) -> None:
        self._storage_forbidden = forbidden

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            headers = {"User-Agent": self._user_agent}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._http = build_client(
                base_url=self._base_url,
                headers=headers,
                timeout=self._timeout,
                transport=self._transport,
            )
        return self._http

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._storage_forbidden:
            raise ProviderError("Bangumi provider forbids source payload storage.")
        return send(self.http, method, path, provider="Bangumi", **kwargs)

    def fetch_calendar(self) -> list[dict[str, Any]]:
        """The weekday board: one entry per weekday with its airing subjects."""
        data = self._request("GET", "/calendar")
        if not isinstance(data, list):
            raise ProviderError("Bangumi /calendar did not return a list.")
        return data

    def _entity(self, namespace: str, identifier: int) -> dict[str, Any]:
        data = self._request("GET", f"/v0/{namespace}s/{int(identifier)}")
        if not isinstance(data, dict):
            raise ProviderError(f"Bangumi {namespace} {identifier} was not an object.")
        if data.get("id") != identifier:
            raise ProviderError(
                f"Bangumi {namespace} {identifier} response identifier is inconsistent."
            )
        return data

    def fetch_subject(self, subject_id: int) -> dict[str, Any]:
        return self._entity("subject", subject_id)

    def fetch_character(self, character_id: int) -> dict[str, Any]:
        return self._entity("character", character_id)

    def fetch_person(self, person_id: int) -> dict[str, Any]:
        return self._entity("person", person_id)

    def search_subjects(
        self,
        *,
        keyword: str,
        subject_types: tuple[int, ...] = (2,),
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        normalized = keyword.strip()
        if not normalized:
            raise ValueError("Bangumi subject search requires a keyword.")
        body: dict[str, Any] = {"keyword": normalized[:512], "sort": "match"}
        if subject_types:
            body["filter"] = {"type": [int(value) for value in subject_types]}
        payload = self._request(
            "POST",
            "/v0/search/subjects",
            params={"limit": min(max(int(limit), 1), 50), "offset": max(0, int(offset))},
            json=body,
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ProviderError("Bangumi subject search response must contain a data list.")
        return payload

    def fetch_subject_episodes(
        self, *, subject_id: int, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        data = self._request(
            "GET",
            "/v0/episodes",
            params={
                "subject_id": subject_id,
                "limit": limit,
                "offset": offset,
            },
        )
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise ProviderError("Bangumi episode response is missing data.")
        return data

    def _relations(self, subject_id: int, endpoint: str) -> list[Any]:
        data = self._request("GET", f"/v0/subjects/{int(subject_id)}/{endpoint}")
        if not isinstance(data, list):
            raise ProviderError(f"Bangumi subject {endpoint} response was not a list.")
        return data

    def fetch_subject_subjects(self, subject_id: int) -> list[Any]:
        return self._relations(subject_id, "subjects")

    def fetch_subject_persons(self, subject_id: int) -> list[Any]:
        return self._relations(subject_id, "persons")

    def fetch_subject_characters(self, subject_id: int) -> list[Any]:
        return self._relations(subject_id, "characters")

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None


__all__ = ["BangumiClient"]
