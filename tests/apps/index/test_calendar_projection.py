from datetime import UTC

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.index.models import AiringBoard, AiringEvent, Entity, Work
from apps.index.services.airing_board import airing_board_service
from apps.users.models import User
from apps.users.services.profile.profile_service import ProfileService

from .projection_fixtures import observation

pytestmark = pytest.mark.django_db


def _anime_work(*, audience: str = Entity.Audience.GENERAL) -> Work:
    entity = Entity.objects.create(
        kind=Entity.Kind.WORK,
        audience=audience,
    )
    return Work.objects.create(entity=entity, work_type=Work.WorkType.ANIME)


def test_calendar_returns_only_current_safe_events_with_provenance() -> None:
    safe_work = _anime_work()
    adult_work = _anime_work(audience=Entity.Audience.ADULT)
    old = observation({"version": "calendar-old"})
    AiringEvent.objects.create(
        work=safe_work,
        weekday=1,
        precision=AiringEvent.Precision.WEEKDAY,
        raw_value="Monday",
        observation=old,
    )
    current = observation({"version": "calendar-current"})
    safe_event = AiringEvent.objects.create(
        work=safe_work,
        weekday=2,
        precision=AiringEvent.Precision.WEEKDAY,
        raw_value="Tuesday",
        observation=current,
    )
    AiringEvent.objects.create(
        work=adult_work,
        weekday=2,
        precision=AiringEvent.Precision.WEEKDAY,
        raw_value="Tuesday",
        observation=current,
    )
    endpoint = "/api/v1/index/calendar/events/"
    client = APIClient()

    anonymous = client.get(endpoint)
    assert anonymous.status_code == 200
    assert [item["id"] for item in anonymous.json()] == [safe_event.id]
    assert anonymous.json()[0]["provenance"]["observation_id"] == str(current.id)

    user = User.objects.create_user(email="calendar-adult@example.com")
    client.force_authenticate(user)
    profile = ProfileService.get_or_create_profile(user=user)
    profile.show_adult_content = True
    profile.adult_content_confirmed_at = timezone.now()
    profile.save(update_fields=["show_adult_content", "adult_content_confirmed_at"])

    confirmed = client.get(endpoint)
    assert {item["work_id"] for item in confirmed.json()} == {
        str(safe_work.entity_id),
        str(adult_work.entity_id),
    }


def test_calendar_without_range_projects_active_board_and_ignores_stale_minutes() -> (
    None
):
    work = _anime_work()
    board_observation = observation({"version": "board"})
    stale_observation = observation({"version": "stale-minute"})
    board_event = AiringEvent.objects.create(
        work=work,
        weekday=2,
        precision=AiringEvent.Precision.WEEKDAY,
        raw_value="Tuesday",
        observation=board_observation,
    )
    AiringEvent.objects.create(
        work=work,
        weekday=3,
        starts_at=timezone.now() - timezone.timedelta(days=90),
        precision=AiringEvent.Precision.MINUTE,
        raw_value="stale",
        observation=stale_observation,
    )
    airing_board_service.refresh(
        observation=board_observation,
        season_key="2026Q3",
        item_count=1,
    )

    response = APIClient().get("/api/v1/index/calendar/events/")

    assert response.status_code == 200
    events = response.json()
    assert [item["id"] for item in events] == [board_event.id]
    assert AiringBoard.objects.filter(status=AiringBoard.Status.ACTIVE).count() == 1


def test_calendar_with_time_range_returns_precise_airings_only() -> None:
    work = _anime_work()
    board_observation = observation({"version": "board"})
    precise_observation = observation({"version": "precise"})
    board_event = AiringEvent.objects.create(
        work=work,
        weekday=2,
        precision=AiringEvent.Precision.WEEKDAY,
        raw_value="Tuesday",
        observation=board_observation,
    )
    precise_event = AiringEvent.objects.create(
        work=work,
        weekday=3,
        starts_at=timezone.datetime(2026, 9, 10, 13, 0, tzinfo=UTC),
        timezone="UTC",
        precision=AiringEvent.Precision.MINUTE,
        raw_value="2026-09-10T13:00:00Z",
        observation=precise_observation,
    )
    airing_board_service.refresh(
        observation=board_observation,
        season_key="2026Q3",
        item_count=1,
    )

    response = APIClient().get(
        "/api/v1/index/calendar/events/",
        {"from": "2026-09-10T00:00:00Z", "to": "2026-09-10T23:59:59Z"},
    )

    assert response.status_code == 200
    events = response.json()
    assert {item["id"] for item in events} == {precise_event.id}
    assert board_event.id not in {item["id"] for item in events}
