"""The VNDB client: query-by-filter over a JSON POST API.

Two behaviours are carried over from the Django client because both are load-bearing:

* An empty result set is a **terminal** 404. VNDB answers 200 with ``results: []`` for a
  deleted or private id, and retrying it can never succeed.
* The provider row can forbid source-payload storage. The check lives with the client so
  a caller cannot forget it.
"""

from __future__ import annotations

from typing import Any

import httpx

from api.worker.providers.catalog import CatalogPage, DeltaPage
from api.worker.providers.errors import ProviderError
from api.worker.providers.http import client as build_client
from api.worker.providers.http import send

VN_FIELDS = (
    "id,title,alttitle,titles.title,titles.lang,titles.latin,titles.official,"
    "released,description,image.url,rating,votecount,length,developers.id,"
    "developers.name,tags.id,tags.name,tags.rating,tags.spoiler,"
    "aliases.name,aliases.latin,aliases.ismain,extlinks.url,extlinks.label"
)


class VNDBClient:
    def __init__(
        self,
        *,
        base_url: str = "https://api.vndb.org/kana",
        user_agent: str = "noshiro-db",
        timeout: float = 30.0,
        http: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url
        self._user_agent = user_agent
        self._timeout = timeout
        self._http = http
        self._storage_forbidden = False

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = build_client(
                base_url=self._base_url,
                headers={"User-Agent": self._user_agent},
                timeout=self._timeout,
            )
        return self._http

    def forbid_storage(self, *, forbidden: bool = True) -> None:
        """Reflect the provider row's storage policy before any request."""
        self._storage_forbidden = forbidden

    def query(
        self,
        endpoint: str,
        *,
        filters: list[Any],
        fields: str,
        page: int = 1,
        results: int = 100,
        count: bool = False,
        sort: str | None = None,
        reverse: bool = False,
    ) -> dict[str, Any]:
        if self._storage_forbidden:
            raise ProviderError("VNDB provider forbids source payload storage.")
        payload: dict[str, Any] = {
            "filters": filters,
            "fields": fields,
            "page": page,
            "results": min(max(results, 1), 100),
            "count": count,
        }
        if sort:
            payload["sort"] = sort
            payload["reverse"] = reverse
        data = send(self.http, "POST", f"/{endpoint}", provider="VNDB", json=payload)
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ProviderError(f"VNDB {endpoint} returned an invalid response.")
        return data

    def fetch_vn(self, vndb_id: str) -> dict[str, Any]:
        data = self.query("vn", filters=["id", "=", vndb_id], fields=VN_FIELDS, results=1)
        if not data["results"]:
            raise ProviderError(
                f"VNDB work {vndb_id} was not found.",
                status_code=404,
                error_code="not_found",
            )
        record: dict[str, Any] = data["results"][0]
        return record

    def discover_vn_page(self, *, cursor: str | None = None, page_size: int = 100) -> CatalogPage:
        page = max(1, int(cursor or "1"))
        data = self.query(
            "vn", filters=[], fields="id", page=page, results=page_size, count=page == 1, sort="id"
        )
        ids = tuple(
            item["id"]
            for item in data["results"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
        return CatalogPage(
            external_ids=ids,
            next_cursor=str(page + 1) if data.get("more") else None,
            total_count=data["count"] if page == 1 and isinstance(data.get("count"), int) else None,
        )

    def discover_vn_delta_page(
        self, *, watermark: str, cursor: str | None = None, page_size: int = 100, seed: int = 0
    ) -> DeltaPage:
        start = int(watermark) if watermark.isdigit() else 0
        if start <= 0:
            start = seed
        page = max(1, int(cursor or "1"))
        data = self.query(
            "vn",
            filters=["id", ">", f"v{start}"],
            fields="id",
            page=page,
            results=page_size,
            sort="id",
        )
        ids = tuple(
            item["id"]
            for item in data["results"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
        highest = max((vn_number(value) for value in ids), default=start)
        return DeltaPage(
            external_ids=ids,
            next_cursor=str(page + 1) if data.get("more") else None,
            watermark=str(highest),
            total_count=data["count"] if isinstance(data.get("count"), int) else None,
        )

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None


def vn_number(external_id: str) -> int:
    raw = str(external_id).lstrip("vV")
    return int(raw) if raw.isdigit() else 0


__all__ = ["VN_FIELDS", "VNDBClient"]
