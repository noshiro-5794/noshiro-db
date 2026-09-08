from unittest.mock import patch

import pytest
from django.utils.timezone import localdate

from apps.index.models import Observation, ProviderNamespace, ProviderRecord
from apps.sync.providers.mal import (
    MAL_SCHEDULE_ITEM_NAMESPACE,
    MAL_SEASON_NAMESPACE,
    mal_api_client,
    season_name_for_quarter,
)
from apps.sync.services.mal_schedule_service import mal_schedule_service

pytestmark = pytest.mark.django_db(transaction=True)


def _current_season() -> tuple[int, int, str]:
    today = localdate()
    quarter = (today.month - 1) // 3 + 1
    return today.year, quarter, season_name_for_quarter(quarter)


def _node(item: dict) -> dict:
    return {"node": item}


def _season_page(items: list[dict], *, has_next: bool = False) -> dict:
    return {
        "data": [_node(item) for item in items],
        "paging": {"next": "https://example.test/next"} if has_next else {},
        "season": {"year": 2026, "season": "summer"},
    }


def test_sync_current_season_records_season_and_item_records() -> None:
    year, quarter, mal_season = _current_season()
    season_key = f"{year}Q{quarter}"
    page_one = _season_page(
        [
            {
                "id": 60636,
                "title": "Bleach",
                "media_type": "tv",
                "status": "currently_airing",
                "start_date": "2026-07-25",
                "broadcast": {"day_of_the_week": "saturday", "start_time": "23:00"},
                "average_episode_duration": 1475,
            },
            {
                "id": 21,
                "title": "One Piece",
                "media_type": "tv",
                "status": "currently_airing",
                "start_date": "1999-10-20",
                "broadcast": {"day_of_the_week": "sunday", "start_time": "23:15"},
                "average_episode_duration": 1440,
            },
        ],
        has_next=True,
    )
    page_two = _season_page(
        [
            {
                "id": 62907,
                "title": "Another Show",
                "media_type": "tv",
                "status": "not_yet_aired",
                "broadcast": {"day_of_the_week": "sunday", "start_time": "22:00"},
                "average_episode_duration": 0,
            }
        ]
    )
    with patch.object(
        mal_api_client,
        "fetch_season",
        side_effect=[page_one, page_two],
    ) as fetch:
        summary = mal_schedule_service.sync_current_season(limit=2, max_pages=5)

    assert summary["season_key"] == season_key
    assert summary["mal_season"] == mal_season
    assert summary["pages"] == 2
    assert summary["items_seen"] == 3
    assert summary["items_recorded"] == 3
    assert fetch.call_count == 2
    first_call = fetch.call_args_list[0]
    assert first_call.kwargs["year"] == year
    assert first_call.kwargs["season"] == mal_season
    assert first_call.kwargs["offset"] == 0
    assert fetch.call_args_list[1].kwargs["offset"] == 2

    season_records = ProviderRecord.objects.filter(
        namespace__provider__slug="mal",
        namespace__slug=MAL_SEASON_NAMESPACE.slug,
    )
    assert season_records.count() == 1
    observation = Observation.objects.get(
        provider_record__in=season_records,
        schema_name="index.schedule",
    )
    normalized = observation.normalized_data
    assert normalized["season_key"] == season_key
    assert normalized["items"][0]["broadcast_day"] == "saturday"
    assert normalized["items"][0]["duration_minutes"] == 25
    assert (
        ProviderRecord.objects.filter(
            namespace__provider__slug="mal",
            namespace__slug=MAL_SCHEDULE_ITEM_NAMESPACE.slug,
        ).count()
        == 3
    )


def test_sync_current_season_is_idempotent() -> None:
    page = _season_page(
        [
            {
                "id": 21,
                "title": "One Piece",
                "media_type": "tv",
                "status": "currently_airing",
                "broadcast": {"day_of_the_week": "sunday", "start_time": "23:15"},
                "average_episode_duration": 1440,
            }
        ]
    )
    with patch.object(mal_api_client, "fetch_season", return_value=page):
        mal_schedule_service.sync_current_season()
        mal_schedule_service.sync_current_season()

    assert (
        ProviderRecord.objects.filter(
            namespace__provider__slug="mal",
            namespace__slug=MAL_SCHEDULE_ITEM_NAMESPACE.slug,
        ).count()
        == 1
    )
    record = ProviderRecord.objects.get(
        namespace__provider__slug="mal",
        namespace__slug=MAL_SCHEDULE_ITEM_NAMESPACE.slug,
        external_id="21",
    )
    assert record.revisions.count() == 1


def test_sync_stops_at_max_pages() -> None:
    page_one = _season_page(
        [
            {
                "id": 21,
                "title": "One Piece",
                "media_type": "tv",
                "status": "currently_airing",
                "broadcast": {"day_of_the_week": "sunday", "start_time": "23:15"},
                "average_episode_duration": 1440,
            }
        ],
        has_next=True,
    )
    page_two = _season_page(
        [
            {
                "id": 22,
                "title": "Another One",
                "media_type": "tv",
                "status": "currently_airing",
                "broadcast": {"day_of_the_week": "monday", "start_time": "23:00"},
                "average_episode_duration": 1440,
            }
        ]
    )
    with patch.object(
        mal_api_client,
        "fetch_season",
        side_effect=[page_one, page_two],
    ) as fetch:
        summary = mal_schedule_service.sync_current_season(limit=1, max_pages=2)

    assert summary["pages"] == 2
    assert summary["items_seen"] == 2
    assert fetch.call_count == 2


def test_sync_returns_mal_source_summary() -> None:
    year, _, mal_season = _current_season()
    page = _season_page([])
    with patch.object(mal_api_client, "fetch_season", return_value=page):
        result = mal_schedule_service.sync()

    assert result["source"] == "mal"
    assert result["season"]["mal_season"] == mal_season
    assert result["season"]["season_key"] == f"{year}Q{_current_season()[1]}"
    assert (
        ProviderNamespace.objects.filter(
            provider__slug="mal",
            slug=MAL_SEASON_NAMESPACE.slug,
        ).exists()
        is True
    )
