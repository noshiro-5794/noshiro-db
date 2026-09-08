from unittest.mock import Mock, patch

import pytest
from django.test import override_settings

from apps.index.models import Provider
from apps.sync.providers.exceptions import MALAPIError
from apps.sync.providers.mal import (
    JIKAN_WEEKDAYS,
    MAL_ANIME_NAMESPACE,
    MAL_SCHEDULE_NAMESPACE,
    MAL_SOURCE,
    JikanClient,
)


def test_mal_namespace_specs_reference_mal_provider() -> None:
    assert MAL_SOURCE.slug == "mal"
    assert MAL_ANIME_NAMESPACE.slug == "anime"
    assert MAL_SCHEDULE_NAMESPACE.slug == "schedule"
    assert all(
        spec.source.slug == "mal"
        for spec in (MAL_ANIME_NAMESPACE, MAL_SCHEDULE_NAMESPACE)
    )


@override_settings(
    JIKAN_API_BASE_URL="https://api.jikan.moe/v4",
    JIKAN_USER_AGENT="Noshiro_5794/noshiro_db (https://github.com/noshiro-5794)",
    JIKAN_TIMEOUT=30,
    JIKAN_RATE_LIMIT_INTERVAL=0.4,
)
def test_jikan_http_client_is_created_lazily() -> None:
    with patch("apps.sync.providers.mal.httpx.Client") as client_factory:
        client = JikanClient()

        client_factory.assert_not_called()

        assert client.client is client_factory.return_value
        client_factory.assert_called_once_with(
            base_url="https://api.jikan.moe/v4",
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "Noshiro_5794/noshiro_db (https://github.com/noshiro-5794)"
                ),
            },
            timeout=30,
            follow_redirects=True,
        )


def test_jikan_season_discovery_uses_page_pagination() -> None:
    http_client = Mock()
    response = http_client.get.return_value
    response.json.return_value = {
        "pagination": {"has_next_page": True},
        "data": [{"mal_id": 1}, {"mal_id": 2}],
    }
    with patch("apps.sync.providers.mal.Provider.objects.filter") as provider_filter:
        provider_filter.return_value.first.return_value = None
        page = JikanClient(http_client).discover_season_now_page(
            cursor="3", page_size=25
        )

    assert page.external_ids == ("1", "2")
    assert page.next_cursor == "4"
    request = http_client.get.call_args
    assert request.args == ("/seasons/now",)
    assert request.kwargs["params"] == {"page": 3, "limit": 25, "sfw": "true"}


def test_jikan_season_discovery_terminates_without_next_page() -> None:
    http_client = Mock()
    response = http_client.get.return_value
    response.json.return_value = {
        "pagination": {"has_next_page": False},
        "data": [{"mal_id": 10}],
    }
    with patch("apps.sync.providers.mal.Provider.objects.filter") as provider_filter:
        provider_filter.return_value.first.return_value = None
        page = JikanClient(http_client).discover_season_now_page(cursor=None)

    assert page.external_ids == ("10",)
    assert page.next_cursor is None


def test_jikan_schedule_discovery_filters_by_weekday() -> None:
    http_client = Mock()
    response = http_client.get.return_value
    response.json.return_value = {
        "pagination": {"has_next_page": False},
        "data": [{"mal_id": 5114}, {"mal_id": 16498}],
    }
    with patch("apps.sync.providers.mal.Provider.objects.filter") as provider_filter:
        provider_filter.return_value.first.return_value = None
        page = JikanClient(http_client).discover_schedule_page(weekday="thursday")

    assert page.external_ids == ("5114", "16498")
    assert page.next_cursor is None
    request = http_client.get.call_args
    assert request.kwargs["params"] == {
        "filter": "thursday",
        "page": 1,
        "limit": 25,
        "sfw": "true",
    }


def test_jikan_schedule_rejects_unknown_weekday() -> None:
    client = JikanClient(Mock())
    with pytest.raises(ValueError, match="Jikan weekday"):
        client.fetch_schedule(weekday="not-a-day")
    assert JIKAN_WEEKDAYS[-1] == "unknown"


def test_jikan_anime_full_record_is_unwrapped() -> None:
    http_client = Mock()
    response = http_client.get.return_value
    response.json.return_value = {"data": {"mal_id": 5114, "title": "Hanasaku Iroha"}}
    with patch("apps.sync.providers.mal.Provider.objects.filter") as provider_filter:
        provider_filter.return_value.first.return_value = None
        anime = JikanClient(http_client).fetch_anime_full(5114)

    assert anime["title"] == "Hanasaku Iroha"
    assert http_client.get.call_args.args == ("/anime/5114/full",)


@pytest.mark.django_db
def test_disabled_mal_provider_is_not_requested() -> None:
    Provider.objects.create(
        slug=MAL_SOURCE.slug,
        name=MAL_SOURCE.name,
        is_enabled=False,
    )
    http_client = Mock()

    with pytest.raises(MALAPIError, match="provider is disabled"):
        JikanClient(http_client).fetch_anime(1)

    http_client.get.assert_not_called()


@pytest.mark.django_db
def test_forbidden_mal_storage_is_not_requested() -> None:
    Provider.objects.create(
        slug=MAL_SOURCE.slug,
        name=MAL_SOURCE.name,
        storage_policy=Provider.UsagePolicy.FORBIDDEN,
    )
    http_client = Mock()

    with pytest.raises(MALAPIError, match="forbids source payload storage"):
        JikanClient(http_client).fetch_anime(1)

    http_client.get.assert_not_called()
