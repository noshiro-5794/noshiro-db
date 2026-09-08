from unittest.mock import patch

import pytest

from apps.index.models import Observation, ProviderNamespace, ProviderRecord
from apps.sync.providers.mal import (
    JIKAN_WEEKDAYS,
    MAL_SCHEDULE_ITEM_NAMESPACE,
    MAL_SCHEDULE_NAMESPACE,
    MAL_SEASON_NAMESPACE,
    jikan_client,
)
from apps.sync.services.mal_schedule_service import mal_schedule_service

pytestmark = pytest.mark.django_db(transaction=True)


def _page(items: list[dict], *, has_next: bool = False) -> dict:
    return {
        "pagination": {"has_next_page": has_next},
        "data": items,
    }


def test_sync_season_now_records_schedule_and_item_records() -> None:
    with patch.object(
        jikan_client,
        "fetch_season_now",
        side_effect=[
            _page(
                [
                    {"mal_id": 1, "title": "One"},
                    {"mal_id": 2, "title": "Two"},
                ],
                has_next=True,
            ),
            _page([{"mal_id": 3, "title": "Three"}]),
        ],
    ):
        summary = mal_schedule_service.sync_season_now(page_size=25, max_pages=3)

    assert summary["pages"] == 2
    assert summary["items_seen"] == 3
    assert summary["items_recorded"] == 3
    season_records = ProviderRecord.objects.filter(
        namespace__provider__slug="mal",
        namespace__slug=MAL_SEASON_NAMESPACE.slug,
    )
    assert season_records.count() == 1
    assert (
        Observation.objects.filter(
            provider_record__in=season_records,
            schema_name="index.schedule",
        ).exists()
        is True
    )
    assert (
        ProviderRecord.objects.filter(
            namespace__provider__slug="mal",
            namespace__slug=MAL_SCHEDULE_ITEM_NAMESPACE.slug,
        ).count()
        == 3
    )


def test_sync_season_now_is_idempotent() -> None:
    payload = _page([{"mal_id": 1, "title": "One"}])
    with patch.object(jikan_client, "fetch_season_now", return_value=payload):
        mal_schedule_service.sync_season_now()
        mal_schedule_service.sync_season_now()

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
        external_id="1",
    )
    assert record.revisions.count() == 1


def test_sync_schedule_day_stores_one_record_per_weekday() -> None:
    payload = _page([{"mal_id": 5114, "title": "Hanasaku Iroha"}])
    with patch.object(jikan_client, "fetch_schedule", return_value=payload):
        summary = mal_schedule_service.sync_schedule_day(weekday="thursday")

    assert summary["pages"] == 1
    assert summary["items_recorded"] == 1
    schedule_record = ProviderRecord.objects.get(
        namespace__provider__slug="mal",
        namespace__slug=MAL_SCHEDULE_NAMESPACE.slug,
        external_id="weekly:thursday",
    )
    assert schedule_record.latest_revision is not None
    assert (
        Observation.objects.filter(
            provider_record=schedule_record,
            schema_name="index.schedule",
        ).exists()
        is True
    )


def test_sync_visits_season_and_all_seven_days() -> None:
    empty_page = _page([])
    with (
        patch.object(
            jikan_client,
            "fetch_season_now",
            return_value=empty_page,
        ),
        patch.object(
            jikan_client,
            "fetch_schedule",
            return_value=empty_page,
        ) as fetch_schedule,
    ):
        mal_schedule_service.sync()

    assert fetch_schedule.call_count == 7
    weekdays = [call.kwargs["weekday"] for call in fetch_schedule.call_args_list]
    assert weekdays == list(JIKAN_WEEKDAYS[:7])
    assert (
        ProviderNamespace.objects.filter(
            provider__slug="mal",
            slug=MAL_SCHEDULE_NAMESPACE.slug,
        ).exists()
        is True
    )
