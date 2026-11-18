import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from api.contexts.synchronization import discovery
from api.worker.providers.anilist import AniListClient
from api.worker.providers.catalog import CatalogPage
from api.worker.providers.errors import ProviderError
from api.worker.providers.vndb import VNDBClient


def test_anilist_full_page_caps_page_size_and_preserves_terminal_cursor():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "data": {
                    "Page": {"pageInfo": {"hasNextPage": False, "total": 1}, "media": [{"id": 12}]}
                }
            },
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://provider.test"
    ) as http:
        page = AniListClient(http=http).discover_anime_page(cursor="2", page_size=100)
    assert page == CatalogPage(("12",), None, 1)
    assert requests[0]["variables"] == {"page": 2, "perPage": 50}


def test_anilist_delta_uses_air_date_watermark_with_boundary_overlap():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "data": {
                    "Page": {
                        "pageInfo": {"hasNextPage": True},
                        "media": [{"id": 12, "startDate": {"year": 2026, "month": 3, "day": 1}}],
                    }
                }
            },
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://provider.test"
    ) as http:
        page = AniListClient(http=http).discover_anime_delta_page(watermark="20260101")
    assert page.watermark == "20260228"
    assert page.next_cursor == "2"
    assert requests[0]["variables"]["startedAfter"] == 20260101
    assert "startDate_greater" in requests[0]["query"]


@pytest.mark.parametrize(
    "fuzzy,previous", [(20240301, 20240229), (20260101, 20251231), (20260000, 20260000), (0, 0)]
)
def test_fuzzy_date_boundaries_match_existing_crawler(fuzzy, previous):
    assert AniListClient._previous_day(fuzzy) == previous


def test_vndb_full_counts_only_first_page():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"results": [{"id": "v12"}], "more": True, "count": 99})

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://provider.test"
    ) as http:
        client = VNDBClient(http=http)
        first = client.discover_vn_page()
        second = client.discover_vn_page(cursor=first.next_cursor)
    assert first.total_count == 99
    assert second.total_count is None
    assert requests[0]["count"] is True and requests[1]["count"] is False
    assert requests[1]["page"] == 2


def test_vndb_delta_is_numeric_and_uses_seed_for_initial_watermark():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"results": [{"id": "v9"}, {"id": "v12"}], "more": False})

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://provider.test"
    ) as http:
        page = VNDBClient(http=http).discover_vn_delta_page(watermark="0", seed=7)
    assert requests[0]["filters"] == ["id", ">", "v7"]
    assert page.watermark == "12"
    assert page.next_cursor is None


@pytest.mark.asyncio
async def test_discovery_obeys_storage_policy_and_closes_transport(monkeypatch):
    requests = []
    http = httpx.Client(
        transport=httpx.MockTransport(lambda request: requests.append(request)),
        base_url="https://provider.test",
    )
    client = VNDBClient(http=http)
    monkeypatch.setattr(discovery, "VNDBClient", lambda: client)
    monkeypatch.setattr(
        discovery, "fetch", AsyncMock(return_value=[SimpleNamespace(storage_policy="forbidden")])
    )
    with pytest.raises(ProviderError):
        await discovery.discover_page(object(), "vndb")
    assert requests == []
    assert http.is_closed


@pytest.mark.asyncio
async def test_bangumi_reconciliation_starts_at_first_record(monkeypatch):
    query = AsyncMock(side_effect=[[SimpleNamespace(external_id="1")], [SimpleNamespace(total=1)]])
    monkeypatch.setattr(discovery, "fetch", query)
    page = await discovery.discover_page(object(), "bangumi", watermark="0", page_size=10)
    assert page.external_ids == ("1",)
    assert page.watermark == "known-record-reconciliation"
    assert query.await_args_list[0].args[2]["offset"] == 0


@pytest.mark.asyncio
async def test_numeric_walk_uses_persisted_frontier(monkeypatch):
    monkeypatch.setenv("MAL_MAX_ANIME_ID", "10")
    monkeypatch.setattr(discovery, "highest_stored_id", AsyncMock(return_value=12))
    monkeypatch.setattr(
        discovery, "read_frontier", AsyncMock(return_value=SimpleNamespace(ceiling=15))
    )
    page = await discovery.discover_page(object(), "mal", cursor="14", page_size=5)
    assert page == CatalogPage(("14", "15"), None, 15)


def test_exhausted_graphql_rate_limit_remains_retryable_by_campaign():
    response = {
        "data": None,
        "errors": [{"message": "rate limit", "extensions": {"code": "RATE_LIMITED"}}],
    }
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response)),
            base_url="https://provider.test",
        ) as http,
        pytest.raises(ProviderError) as caught,
    ):
        AniListClient(http=http, sleep=lambda _: None).discover_anime_page()
    assert caught.value.status_code == 429
    assert caught.value.retryable
