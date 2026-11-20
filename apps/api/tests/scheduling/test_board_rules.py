from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from api.contexts.scheduling import board_rules as rules
from api.worker.board_projection import board_window, project


def test_rolling_window_and_grace_boundary():
    start, end = board_window(datetime(2026, 11, 18, tzinfo=UTC))
    assert start.isoformat() == "2026-09-30T15:00:00+00:00"
    assert end.isoformat() == "2026-12-31T15:00:00+00:00"
    assert not rules.season_switch_allowed("2026Q4", today=date(2026, 10, 3))
    assert rules.season_switch_allowed("2026Q4", today=date(2026, 10, 4))


@pytest.mark.parametrize(
    "format_name,allowed", [("TV", True), ("web", True), ("MUSIC", False), ("", True)]
)
def test_calendar_format_gate(format_name, allowed):
    assert rules.format_allowed(format_name) == allowed


def test_anilist_instant_and_mal_corroboration_preserve_field_roles():
    identifier = uuid4()
    instant = datetime(2026, 11, 18, tzinfo=UTC)
    precise = rules.CandidateBar(
        identifier, 3, starts_at=instant, precision="minute", provider="anilist"
    )
    weekly = rules.CandidateBar(identifier, 3, precision="weekday", provider="mal")
    result = project([weekly, precise], {identifier})[0]
    assert result["decision"] == "consensus"
    assert result["starts_at"] == instant.isoformat()
    assert [item["role"] for item in result["source_refs"]] == ["precise", "weekday-corroboration"]


def test_mal_movie_is_date_only_and_music_is_excluded():
    identifier = uuid4()
    arguments = {
        "mal_works": {1: identifier},
        "observation_id": uuid4(),
        "now": datetime(2026, 10, 1, tzinfo=UTC),
        "end": datetime(2027, 1, 1, tzinfo=UTC),
    }
    item = {
        "mal_id": 1,
        "media_type": "movie",
        "status": "finished_airing",
        "start_date": "2026-11-01",
    }
    bar = rules.mal_item_bar(item=item, **arguments)
    assert bar.weekday is None and bar.precision == "day"
    assert bar.starts_at.isoformat() == "2026-10-31T15:00:00+00:00"
    assert rules.mal_item_bar(item={**item, "media_type": "music"}, **arguments) is None


def test_mal_upcoming_premiere_and_invalid_time_fallback():
    identifier = uuid4()
    arguments = {
        "mal_works": {1: identifier},
        "observation_id": None,
        "now": datetime(2026, 10, 1, tzinfo=UTC),
        "end": datetime(2027, 1, 1, tzinfo=UTC),
    }
    item = {
        "mal_id": 1,
        "media_type": "tv",
        "status": "not_yet_aired",
        "start_date": "2026-11-01",
        "broadcast_day": "sunday",
        "broadcast_time": "23:00",
        "timezone": "Asia/Tokyo",
    }
    bar = rules.mal_item_bar(item=item, **arguments)
    assert bar.starts_at.isoformat() == "2026-11-01T14:00:00+00:00"
    fallback = rules.mal_item_bar(item={**item, "broadcast_time": "invalid"}, **arguments)
    assert fallback.starts_at is None and fallback.precision == "weekday"
