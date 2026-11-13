"""Provider transport behaviour, exercised through httpx's mock transport.

No network: every case here is an answer a provider could give, including the ones that
are easy to get wrong — an empty result set that means "gone", a 429 that carries its own
back-off, and a body that is not JSON at all.
"""

from __future__ import annotations

import httpx
import pytest

from api.worker.providers.errors import ProviderError
from api.worker.providers.http import send, should_proxy
from api.worker.providers.vndb import VNDBClient


def vndb(handler) -> VNDBClient:
    transport = httpx.MockTransport(handler)
    return VNDBClient(http=httpx.Client(transport=transport, base_url="https://api.vndb.org/kana"))


def test_a_work_is_returned_as_the_first_result() -> None:
    client = vndb(lambda request: httpx.Response(200, json={"results": [{"id": "v17"}]}))
    assert client.fetch_vn("v17")["id"] == "v17"


def test_an_empty_result_set_is_a_terminal_not_found() -> None:
    client = vndb(lambda request: httpx.Response(200, json={"results": []}))
    with pytest.raises(ProviderError) as caught:
        client.fetch_vn("v0")
    assert caught.value.is_not_found
    assert not caught.value.retryable


def test_a_404_is_not_found() -> None:
    client = vndb(lambda request: httpx.Response(404, text="no such record"))
    with pytest.raises(ProviderError) as caught:
        client.fetch_vn("v1")
    assert caught.value.status_code == 404
    assert caught.value.is_not_found


def test_a_429_keeps_the_providers_back_off_hint() -> None:
    client = vndb(
        lambda request: httpx.Response(429, headers={"retry-after": "7"}, text="slow down")
    )
    with pytest.raises(ProviderError) as caught:
        client.fetch_vn("v1")
    assert caught.value.retryable
    assert caught.value.retry_after == 7.0
    assert not caught.value.is_not_found


def test_a_server_error_is_retryable() -> None:
    client = vndb(lambda request: httpx.Response(503, text="down"))
    with pytest.raises(ProviderError) as caught:
        client.fetch_vn("v1")
    assert caught.value.retryable


def test_invalid_json_is_reported_as_such() -> None:
    client = vndb(lambda request: httpx.Response(200, text="<html>not json</html>"))
    with pytest.raises(ProviderError) as caught:
        client.fetch_vn("v1")
    assert caught.value.error_code == "invalid_json"
    assert caught.value.retryable


def test_a_malformed_body_is_rejected() -> None:
    client = vndb(lambda request: httpx.Response(200, json={"results": "nope"}))
    with pytest.raises(ProviderError):
        client.fetch_vn("v1")


def test_a_forbidden_storage_policy_blocks_the_request() -> None:
    client = vndb(lambda request: httpx.Response(200, json={"results": []}))
    client.forbid_storage()
    with pytest.raises(ProviderError, match="forbids"):
        client.fetch_vn("v1")


def test_transport_errors_become_provider_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = vndb(handler)
    with pytest.raises(ProviderError) as caught:
        client.fetch_vn("v1")
    assert caught.value.error_code == "transport_error"
    assert caught.value.retryable


def test_send_rejects_a_path_outside_the_base_url() -> None:
    http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    with pytest.raises(ProviderError):
        send(http, "GET", "https://elsewhere.invalid/x", provider="test")


def test_proxy_is_skipped_for_configured_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OUTBOUND_PROXY_URL", "http://192.168.3.222:7890")
    monkeypatch.setenv("OUTBOUND_NO_PROXY_HOSTS", "api.vndb.org,localhost")
    assert not should_proxy("https://api.vndb.org/kana/vn")
    assert should_proxy("https://example.com/x")
