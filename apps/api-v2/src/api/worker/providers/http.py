"""The shared transport every provider client sits on.

Proxy configuration is read from the environment because the workers run in containers:
the host's proxy is reachable at the host address, never at ``127.0.0.1`` inside the
container. Keeping that here means a client cannot accidentally hard-code the wrong
address.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from api.worker.providers.errors import ProviderError, retry_after_seconds


def _proxy() -> str | None:
    url = os.environ.get("OUTBOUND_PROXY_URL", "").strip()
    return url or None


def _no_proxy_hosts() -> set[str]:
    raw = os.environ.get("OUTBOUND_NO_PROXY_HOSTS", "")
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def should_proxy(url: str) -> bool:
    """Whether a request to this URL should go through the outbound proxy."""
    if not _proxy():
        return False
    host = httpx.URL(url).host.lower()
    return not any(host == blocked or host.endswith("." + blocked) for blocked in _no_proxy_hosts())


def client(
    *,
    base_url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """A client for one provider, with the proxy applied when it is configured."""
    kwargs: dict[str, Any] = {
        "base_url": base_url,
        "timeout": timeout,
        "follow_redirects": True,
        "headers": {"Accept": "application/json", **(headers or {})},
    }
    if transport is not None:
        kwargs["transport"] = transport
    elif should_proxy(base_url):
        kwargs["proxy"] = _proxy()
    return httpx.Client(**kwargs)


def send(
    http: httpx.Client,
    method: str,
    path: str,
    *,
    provider: str,
    **kwargs: Any,
) -> Any:
    """Perform one request and translate every failure into a ProviderError.

    ``path`` must stay relative to the client's base URL: a provider client that
    accepted an absolute URL could be talked into calling somewhere else entirely.
    """
    if "://" in path:
        raise ProviderError(f"{provider} refused an absolute URL: {path}")
    try:
        response = http.request(method, path, **kwargs)
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        response = error.response
        detail = response.text[:500]
        raise ProviderError(
            f"{provider} {path} returned {response.status_code}: {detail}",
            status_code=response.status_code,
            retry_after=retry_after_seconds(response.headers),
            error_code="not_found" if response.status_code == 404 else "http_error",
        ) from error
    except httpx.RequestError as error:
        raise ProviderError(
            f"{provider} {path} request failed: {error}",
            error_code="transport_error",
        ) from error
    try:
        return response.json()
    except (json.JSONDecodeError, ValueError) as error:
        raise ProviderError(
            f"{provider} {path} returned invalid JSON.",
            error_code="invalid_json",
        ) from error


__all__ = ["client", "send", "should_proxy"]
