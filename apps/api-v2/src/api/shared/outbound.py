"""Outbound proxy selection shared by external HTTP clients."""

import os

import httpx


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


def proxy_for(url: str) -> str | None:
    return _proxy() if should_proxy(url) else None
