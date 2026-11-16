"""The calendar payload helpers, where a wrong answer silently drops a show."""

from __future__ import annotations

from types import SimpleNamespace

from api.worker.calendar import (
    board_metadata,
    build_event,
    calendar_items,
    collection_doing,
    count_calendar_items,
    diff_ids,
    ids_from_groups,
    weekday_counts,
    weekday_number,
    weekday_raw_value,
)

GROUPED = [
    {"weekday": {"id": 1, "en": "Mon"}, "items": [{"id": 10}, {"id": 11}]},
    {"weekday": {"id": 7, "en": "Sun"}, "items": [{"id": 12}]},
]


def test_a_weekday_number_wins_over_its_name() -> None:
    assert weekday_number({"id": 3, "en": "Sunday"}) == 3


def test_a_name_is_used_when_the_number_is_missing_or_out_of_range() -> None:
    assert weekday_number({"en": "Thursday"}) == 4
    assert weekday_number({"id": 9, "en": "Fri"}) == 5


def test_an_unknown_weekday_is_none_rather_than_guessed() -> None:
    assert weekday_number({"en": "Someday"}) is None
    assert weekday_number({}) is None


def test_the_label_falls_back_from_english_to_japanese_to_chinese() -> None:
    assert weekday_raw_value({"en": "Mon"}) == "Mon"
    assert weekday_raw_value({"en": "", "ja": "月"}) == "月"
    assert weekday_raw_value({"cn": "周一"}) == "周一"
    assert weekday_raw_value({}) == ""


def test_only_items_with_an_integer_id_are_kept() -> None:
    assert ids_from_groups(GROUPED) == {10, 11, 12}
    messy = [{"items": [{"id": "12"}, {"nope": 1}, 5]}]
    assert ids_from_groups(messy) == set()


def test_a_boolean_id_is_accepted_because_the_old_service_does() -> None:
    """A quirk kept for parity, not an endorsement.

    ``isinstance(True, int)`` is true in Python, so the Django helper accepts a boolean id
    and this port reproduces it. Bangumi never sends one; changing the rule here would make
    the two implementations disagree on a payload that does not exist, which is worse than
    carrying the quirk.
    """
    assert ids_from_groups([{"items": [{"id": True}]}]) == {True}


def test_the_item_count_survives_malformed_groups() -> None:
    assert count_calendar_items(GROUPED) == 3
    assert count_calendar_items([None, {"items": "x"}, {"items": []}]) == 0


def test_unreadable_collection_counts_are_zero() -> None:
    assert collection_doing({"collection": {"doing": 12}}) == 12
    assert collection_doing({"collection": {"doing": -1}}) == 0
    assert collection_doing({"collection": {"doing": True}}) == 0
    assert collection_doing({}) == 0


def test_weekday_counts_are_keyed_by_string_and_skip_unknowns() -> None:
    events = [
        SimpleNamespace(weekday=1),
        SimpleNamespace(weekday=1),
        SimpleNamespace(weekday=7),
        SimpleNamespace(weekday=None),
    ]
    assert weekday_counts(events) == {"1": 2, "7": 1}


def test_the_flattened_items_keep_their_payload_shape() -> None:
    assert [item["id"] for item in calendar_items(GROUPED)] == [10, 11, 12]


def test_an_event_degrades_to_unknown_when_the_weekday_is_missing() -> None:
    event = build_event(work_id="w", weekday={"en": "Someday"}, item={"id": 1})
    assert event["weekday"] is None
    assert event["precision"] == "unknown"
    assert event["raw_value"] == "Someday"


def test_an_event_carries_the_watching_count() -> None:
    event = build_event(
        work_id="w",
        weekday={"id": 3, "en": "Wed"},
        item={"id": 1, "collection": {"doing": 42}},
    )
    assert event == {
        "work_id": "w",
        "weekday": 3,
        "precision": "weekday",
        "raw_value": "Wed",
        "collection_doing": 42,
    }


def test_the_diff_reports_both_directions_sorted() -> None:
    added, removed = diff_ids({3, 1, 2}, {2, 4})
    assert added == [1, 3]
    assert removed == [4]


def test_identical_sets_diff_to_nothing() -> None:
    assert diff_ids({1, 2}, {1, 2}) == ([], [])


def test_the_metadata_counts_by_weekday_and_records_the_diff() -> None:
    events = [SimpleNamespace(weekday=1), SimpleNamespace(weekday=None)]
    metadata = board_metadata(
        fetched_at="2026-01-01T00:00:00Z",
        events=events,
        added_ids=[9],
        removed_ids=[4],
    )
    assert metadata == {
        "fetched_at": "2026-01-01T00:00:00Z",
        "weekday_counts": {"1": 1},
        "added_ids": [9],
        "removed_ids": [4],
    }
