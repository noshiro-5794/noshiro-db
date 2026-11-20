"""The MAL client against a mock transport.

Retries are the interesting part: they must happen for the statuses that can succeed on a
second try, must respect the provider's own back-off hint, and must stop.
"""

from __future__ import annotations

import httpx
import pytest

from api.worker.providers.errors import ProviderError
from api.worker.providers.mal import MALClient, season_name_for_quarter


def mal(handler, *, slept: list[float] | None = None, client_id: str = "test-id") -> MALClient:
    transport = httpx.MockTransport(handler)
    return MALClient(
        client_id=client_id,
        http=httpx.Client(transport=transport, base_url="https://api.myanimelist.net/v2"),
        sleep=(slept.append if slept is not None else (lambda _seconds: None)),
    )


def test_a_record_is_returned() -> None:
    client = mal(lambda request: httpx.Response(200, json={"id": 7}))
    assert client.fetch_anime(7)["id"] == 7


def test_a_503_is_retried_and_can_succeed() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json={"id": 7})

    slept: list[float] = []
    client = mal(handler, slept=slept)
    assert client.fetch_anime(7)["id"] == 7
    assert calls["n"] == 2
    assert slept == [10.0], "a 5xx waits its default before retrying"


def test_retry_after_wins_over_the_default_wait() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "2"}, text="slow")
        return httpx.Response(200, json={"id": 7})

    slept: list[float] = []
    mal(handler, slept=slept).fetch_anime(7)
    assert slept == [2.0]


def test_the_retry_budget_is_bounded() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, text="busy")

    with pytest.raises(ProviderError) as caught:
        mal(handler).fetch_anime(7)
    assert calls["n"] == 3
    assert caught.value.retryable


def test_a_404_is_terminal() -> None:
    client = mal(lambda request: httpx.Response(404, text="gone"))
    with pytest.raises(ProviderError) as caught:
        client.fetch_anime(1)
    assert caught.value.is_not_found
    assert not caught.value.retryable


def test_invalid_json_is_reported() -> None:
    client = mal(lambda request: httpx.Response(200, text="<html>"))
    with pytest.raises(ProviderError) as caught:
        client.fetch_anime(1)
    assert caught.value.error_code == "invalid_json"


def test_a_missing_client_id_refuses_before_sending(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAL_API_CLIENT_ID", raising=False)
    client = MALClient(client_id="")
    with pytest.raises(ProviderError, match="MAL_API_CLIENT_ID"):
        client.fetch_anime(1)


def test_a_forbidden_storage_policy_blocks_the_request() -> None:
    client = mal(lambda request: httpx.Response(200, json={"id": 1}))
    client.forbid_storage()
    with pytest.raises(ProviderError, match="forbids"):
        client.fetch_anime(1)


def test_discovery_walks_the_id_space_up_to_the_ceiling() -> None:
    client = mal(lambda request: httpx.Response(200, json={}))
    ids, cursor = client.discover_anime_page(ceiling=10, cursor=None, page_size=4)
    assert ids == ["1", "2", "3", "4"]
    assert cursor == "5"
    ids, cursor = client.discover_anime_page(ceiling=10, cursor="9", page_size=4)
    assert ids == ["9", "10"]
    assert cursor is None


def test_discovery_past_the_ceiling_returns_nothing() -> None:
    client = mal(lambda request: httpx.Response(200, json={}))
    assert client.discover_anime_page(ceiling=10, cursor="11") == ([], None)


def test_season_names_come_from_the_quarter() -> None:
    assert season_name_for_quarter(1) == "winter"
    assert season_name_for_quarter(4) == "fall"
    with pytest.raises(ValueError):
        season_name_for_quarter(5)
