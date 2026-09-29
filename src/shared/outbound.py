from typing import Any
from urllib.parse import urlparse

from django.conf import settings


def outbound_proxies() -> dict[str, str] | None:
    proxy_url = getattr(settings, "OUTBOUND_PROXY_URL", "") or ""
    if not proxy_url:
        return None
    return {
        "http://": proxy_url,
        "https://": proxy_url,
    }


def host_bypasses_proxy(host: str) -> bool:
    """Match a host against OUTBOUND_NO_PROXY_HOSTS with suffix semantics.

    The list mirrors the NO_PROXY convention, so an entry like ``myanimelist.net``
    also covers ``api.myanimelist.net``.
    """
    host = (host or "").strip().lower()
    if not host:
        return False
    for entry in getattr(settings, "OUTBOUND_NO_PROXY_HOSTS", ()) or ():
        candidate = str(entry).strip().lower()
        if candidate and (host == candidate or host.endswith(f".{candidate}")):
            return True
    return False


def httpx_client_kwargs(*, use_proxy: bool = True, **kwargs: Any) -> dict[str, Any]:
    # Passing a proxy explicitly makes httpx ignore NO_PROXY, so the exclusion
    # list has to be applied here. Providers that must never be proxied also
    # pass use_proxy=False.
    host = urlparse(str(kwargs.get("base_url") or "")).hostname or ""
    if use_proxy and not host_bypasses_proxy(host):
        proxies = outbound_proxies()
        if proxies is not None:
            kwargs.setdefault("proxy", proxies["http://"])
    return kwargs
