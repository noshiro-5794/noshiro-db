"""The Bangumi client against a mock transport."""

from __future__ import annotations

import httpx
import pytest

from api.integrations.providers.bangumi import BangumiClient
from api.integrations.providers.errors import ProviderError


def bangumi(handler, **kwargs) -> BangumiClient:
    return BangumiClient(transport=httpx.MockTransport(handler), **kwargs)


def test_the_calendar_returns_the_weekday_board() -> None:
    payload = [{"weekday": {"id": 1, "en": "Mon"}, "items": []}]
    client = bangumi(lambda request: httpx.Response(200, json=payload))
    assert client.fetch_calendar() == payload


def test_a_calendar_that_is_not_a_list_is_rejected() -> None:
    client = bangumi(lambda request: httpx.Response(200, json={"oops": True}))
    with pytest.raises(ProviderError, match="did not return a list"):
        client.fetch_calendar()


def test_a_subject_is_fetched_by_id() -> None:
    client = bangumi(lambda request: httpx.Response(200, json={"id": 42}))
    assert client.fetch_subject(42)["id"] == 42


def test_a_missing_subject_is_a_terminal_not_found() -> None:
    client = bangumi(lambda request: httpx.Response(404, text="not found"))
    with pytest.raises(ProviderError) as caught:
        client.fetch_subject(1)
    assert caught.value.is_not_found
    assert not caught.value.retryable


def test_a_server_error_is_retryable() -> None:
    client = bangumi(lambda request: httpx.Response(502, text="bad gateway"))
    with pytest.raises(ProviderError) as caught:
        client.fetch_subject(1)
    assert caught.value.retryable


def test_a_forbidden_storage_policy_blocks_before_sending() -> None:
    client = bangumi(lambda request: httpx.Response(200, json=[]))
    client.forbid_storage()
    with pytest.raises(ProviderError, match="forbids"):
        client.fetch_calendar()


def test_the_api_key_is_sent_only_when_configured() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, json=[])

    bangumi(handler, api_key="secret").fetch_calendar()
    assert seen["auth"] == "Bearer secret"
    bangumi(handler, api_key="").fetch_calendar()
    assert seen["auth"] == ""


def test_subject_search_posts_bounded_anime_filter():
    import json

    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [{"id": 42}], "total": 1})

    client = bangumi(handler)
    try:
        assert client.search_subjects(keyword="  Anime  ", limit=500, offset=-1)["total"] == 1
        request = seen[0]
        assert request.method == "POST"
        assert request.url.path == "/v0/search/subjects"
        assert request.url.params["limit"] == "50" and request.url.params["offset"] == "0"
        assert json.loads(request.content) == {
            "keyword": "Anime",
            "sort": "match",
            "filter": {"type": [2]},
        }
        with pytest.raises(ValueError):
            client.search_subjects(keyword=" ")
    finally:
        client.close()


def test_subject_search_rejects_missing_data_list():
    client = bangumi(lambda request: httpx.Response(200, json={}))
    try:
        with pytest.raises(ProviderError, match="data list"):
            client.search_subjects(keyword="Anime")
    finally:
        client.close()
