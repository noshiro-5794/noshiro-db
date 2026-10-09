from django.test import override_settings

from shared.outbound import (
    host_bypasses_proxy,
    httpx_client_kwargs,
    outbound_proxies,
)


@override_settings(OUTBOUND_PROXY_URL="http://proxy.local:7890")
def test_outbound_proxy_configuration_is_explicit_for_http_clients() -> None:
    assert outbound_proxies() == {
        "http://": "http://proxy.local:7890",
        "https://": "http://proxy.local:7890",
    }

    assert httpx_client_kwargs(timeout=3) == {
        "timeout": 3,
        "proxy": "http://proxy.local:7890",
    }


@override_settings(OUTBOUND_PROXY_URL="")
def test_outbound_proxy_is_optional() -> None:
    assert outbound_proxies() is None
    assert httpx_client_kwargs(timeout=3) == {"timeout": 3}


class TestNoProxyHosts:
    """A listed host must reach the provider directly, proxy or not.

    Passing a proxy to httpx disables its NO_PROXY handling, so a broken proxy
    took down every host on the exclusion list until this was applied by hand.
    """

    @override_settings(
        OUTBOUND_PROXY_URL="http://proxy.local:7890",
        OUTBOUND_NO_PROXY_HOSTS=("api.vndb.org", "myanimelist.net"),
    )
    def test_listed_host_skips_the_proxy(self) -> None:
        assert host_bypasses_proxy("api.vndb.org") is True
        assert host_bypasses_proxy("api.myanimelist.net") is True
        assert httpx_client_kwargs(base_url="https://api.vndb.org/kana") == {
            "base_url": "https://api.vndb.org/kana"
        }

    @override_settings(
        OUTBOUND_PROXY_URL="http://proxy.local:7890",
        OUTBOUND_NO_PROXY_HOSTS=("api.vndb.org",),
    )
    def test_unlisted_host_still_uses_the_proxy(self) -> None:
        assert host_bypasses_proxy("api.bgm.tv") is False
        assert httpx_client_kwargs(base_url="https://api.bgm.tv") == {
            "base_url": "https://api.bgm.tv",
            "proxy": "http://proxy.local:7890",
        }
