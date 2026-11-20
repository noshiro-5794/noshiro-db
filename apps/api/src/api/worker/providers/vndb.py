"""The VNDB client: query-by-filter over a JSON POST API.

Two behaviours are carried over from the Django client because both are load-bearing:

* An empty result set is a **terminal** 404. VNDB answers 200 with ``results: []`` for a
  deleted or private id, and retrying it can never succeed.
* The provider row can forbid source-payload storage. The check lives with the client so
  a caller cannot forget it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from api.worker.providers.catalog import CatalogPage, DeltaPage
from api.worker.providers.errors import ProviderError
from api.worker.providers.http import client as build_client
from api.worker.providers.http import send

VN_FIELDS = (
    "id,title,alttitle,aliases,released,languages,platforms,olang,description,"
    "length_minutes,length_votes,devstatus,popularity,rating,votecount,titles.lang,"
    "titles.title,titles.latin,titles.official,titles.main,image.url,image.sexual,"
    "image.violence,screenshots.url,screenshots.sexual,screenshots.violence,"
    "screenshots.release.id,developers.id,developers.name,developers.original,"
    "developers.type,developers.extlinks.url,developers.extlinks.label,tags.id,tags.name,"
    "tags.rating,tags.spoiler,tags.lie,relations.id,relations.title,relations.alttitle,"
    "relations.olang,relations.relation,relations.relation_official,staff.id,staff.aid,"
    "staff.name,staff.original,staff.lang,staff.role,staff.note,va.staff.id,va.staff.aid,"
    "va.staff.name,va.staff.original,va.staff.lang,va.character.id,va.character.name,"
    "va.character.original,va.note,extlinks.url,extlinks.label"
)


RELEASE_FIELDS = (
    "id,title,alttitle,released,languages.lang,languages.title,languages.latin,"
    "languages.main,languages.mtl,platforms,media.medium,media.qty,resolution,voiced,"
    "engine,official,patch,freeware,uncensored,minage,vns.id,vns.title,vns.rtype,"
    "producers.id,producers.name,producers.original,producers.type,producers.developer,"
    "producers.publisher,producers.extlinks.url,producers.extlinks.label,extlinks.url,"
    "extlinks.label"
)


CHARACTER_FIELDS = (
    "id,name,original,aliases,description,image.url,image.sexual,image.violence,sex,"
    "gender,blood_type,height,weight,bust,waist,hips,cup,birthday,age,vns.id,vns.role,"
    "vns.spoiler,vns.release.id,traits.id,traits.name,traits.group_id,traits.group_name,"
    "traits.spoiler,traits.lie"
)


STAFF_FIELDS = (
    "id,aid,ismain,name,original,lang,description,gender,aliases.aid,aliases.name,"
    "aliases.latin,aliases.ismain,extlinks.url,extlinks.label"
)


@dataclass(frozen=True, slots=True)
class VNDBImportBatch:
    work: dict[str, Any]
    releases: tuple[dict[str, Any], ...] = ()
    characters: tuple[dict[str, Any], ...] = ()
    contributors: tuple[dict[str, Any], ...] = ()
    related_fetched: bool = False


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

    def fetch_related(self, endpoint: str, *, vndb_id: str, fields: str) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []
        while True:
            filters: list[Any] = ["vn", "=", ["id", "=", vndb_id]]
            data = self.query(endpoint, filters=filters, fields=fields, page=page)
            items.extend(data["results"])
            if not data.get("more"):
                return items
            page += 1

    def fetch_import_batch(self, vndb_id: str, *, include_related: bool = True) -> VNDBImportBatch:
        work = self.fetch_vn(vndb_id)
        if not include_related:
            return VNDBImportBatch(work=work)
        staff_ids = self._embedded_staff_ids(work)
        contributors = self._fetch_staff_details(work) if staff_ids else ()
        return VNDBImportBatch(
            work=work,
            releases=tuple(self.fetch_related("release", vndb_id=vndb_id, fields=RELEASE_FIELDS)),
            characters=tuple(
                self.fetch_related("character", vndb_id=vndb_id, fields=CHARACTER_FIELDS)
            ),
            contributors=contributors,
            related_fetched=True,
        )

    @classmethod
    def _embedded_staff_ids(cls, work: dict[str, Any]) -> tuple[str, ...]:
        """Staff ids referenced by a VN payload (staff and voice-actor entries).

        ``/staff`` accepts only scalar ``id`` filters and has no ``vn`` filter,
        so per-id detail fetches are driven from ids the work already embeds.
        """
        entries = list(work.get("staff") or [])
        entries.extend(
            entry.get("staff") for entry in work.get("va") or [] if isinstance(entry, dict)
        )
        ids: list[str] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            identifier = item.get("id")
            if isinstance(identifier, int) and not isinstance(identifier, bool) and identifier > 0:
                identifier = f"s{identifier}"
            if (
                isinstance(identifier, str)
                and identifier.startswith("s")
                and identifier[1:].isascii()
                and identifier[1:].isdigit()
                and int(identifier[1:]) > 0
            ):
                ids.append(identifier)
        return tuple(dict.fromkeys(ids))

    def _fetch_staff_details(self, work: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        details: list[dict[str, Any]] = []
        for staff_id in self._embedded_staff_ids(work):
            data = self.query(
                "staff",
                filters=["and", ["ismain", "=", 1], ["id", "=", staff_id]],
                fields=STAFF_FIELDS,
                results=1,
            )
            if data.get("results"):
                details.append(data["results"][0])
        return tuple(details)

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None


def vn_number(external_id: str) -> int:
    raw = str(external_id).lstrip("vV")
    return int(raw) if raw.isdigit() else 0


__all__ = ["VN_FIELDS", "VNDBClient"]
