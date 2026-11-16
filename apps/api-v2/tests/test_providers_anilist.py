"""The AniList client against a mock transport.

The interesting part is not HTTP status: GraphQL answers 200 with an ``errors`` array, so
the retry decisions live in the body.
"""

from __future__ import annotations

import httpx
import pytest

from api.worker.providers.anilist import AniListClient
from api.worker.providers.errors import ProviderError


def anilist(handler, slept: list[float] | None = None) -> AniListClient:
    return AniListClient(
        transport=httpx.MockTransport(handler),
        sleep=(slept.append if slept is not None else (lambda _s: None)),
    )


def test_media_is_returned_from_the_data_envelope() -> None:
    client = anilist(lambda request: httpx.Response(200, json={"data": {"Media": {"id": 1}}}))
    assert client.fetch_media(1)["id"] == 1


def test_a_null_media_is_a_terminal_not_found() -> None:
    client = anilist(lambda request: httpx.Response(200, json={"data": {"Media": None}}))
    with pytest.raises(ProviderError) as caught:
        client.fetch_media(1)
    assert caught.value.is_not_found
    assert not caught.value.retryable


def test_rate_limited_is_retried_and_can_succeed() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                200,
                json={
                    "data": None,
                    "errors": [{"message": "slow down", "extensions": {"code": "RATE_LIMITED"}}],
                },
            )
        return httpx.Response(200, json={"data": {"Media": {"id": 7}}})

    slept: list[float] = []
    assert anilist(handler, slept).fetch_media(7)["id"] == 7
    assert slept == [5.0]


def test_a_maintenance_message_is_not_retried() -> None:
    client = anilist(
        lambda request: httpx.Response(
            200,
            json={"data": None, "errors": [{"message": "Service temporarily disabled"}]},
        )
    )
    with pytest.raises(ProviderError) as caught:
        client.fetch_media(1)
    assert caught.value.status_code == 403
    assert caught.value.retry_after == 900
    assert caught.value.error_code == "provider_maintenance"


def test_an_unknown_graphql_error_is_terminal() -> None:
    client = anilist(
        lambda request: httpx.Response(
            200, json={"data": None, "errors": [{"message": "bad query"}]}
        )
    )
    with pytest.raises(ProviderError, match="bad query"):
        client.fetch_media(1)


def test_a_missing_data_envelope_is_rejected() -> None:
    client = anilist(lambda request: httpx.Response(200, json={"errors": []}))
    with pytest.raises(ProviderError, match="invalid GraphQL response"):
        client.fetch_media(1)


def test_http_500_is_retried_a_bounded_number_of_times() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, text="down")

    with pytest.raises(ProviderError):
        anilist(handler).fetch_media(1)
    assert calls["n"] == 3


def test_a_forbidden_storage_policy_blocks_the_request() -> None:
    client = anilist(lambda request: httpx.Response(200, json={"data": {}}))
    client.forbid_storage()
    with pytest.raises(ProviderError, match="forbids"):
        client.fetch_media(1)
