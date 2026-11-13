"""The MAL mapper's decisions, which the shadow comparison depends on.

These are pure functions: no database, no network. They pin what a payload contributes to
names and facts, including the cases the comparison against Django caught.
"""

from __future__ import annotations

from api.worker.entities import work_type_for
from api.worker.mal_import import fact_candidates, name_entries

PAYLOAD = {
    "id": 1,
    "title": "Romanised Title",
    "alternative_titles": {"en": "English Title", "ja": "日本語", "synonyms": ["Alt"]},
    "start_date": "2020-04-05",
    "end_date": "",
    "media_type": "tv",
    "status": "finished_airing",
    "num_episodes": 12,
    "mean": 8.1,
    "rank": 300,
    "popularity": 42,
    "num_list_users": 500000,
    "start_season": {"year": 2020, "season": "spring"},
    "broadcast": {"day_of_the_week": "sunday", "start_time": "00:30"},
    "average_episode_duration": 1420,
}


def test_names_keep_the_provider_kinds() -> None:
    entries = name_entries(PAYLOAD)
    assert ("Romanised Title", "", "romanized") in entries
    assert ("English Title", "en", "official") in entries
    assert ("日本語", "ja", "original") in entries
    assert ("Alt", "", "alias") in entries


def test_a_payload_without_titles_produces_no_names() -> None:
    assert name_entries({"id": 2}) == []


def test_a_non_string_synonym_is_ignored() -> None:
    entries = name_entries({"id": 3, "alternative_titles": {"synonyms": [None, "ok"]}})
    assert entries == [("ok", "", "alias")]


def test_facts_carry_their_declared_type() -> None:
    facts = fact_candidates(PAYLOAD)
    assert facts["episode-count"] == (12, "number")
    assert facts["mal-type"] == ("tv", "string")
    assert facts["release-date"] == ("2020-04-05", "date")


def test_duration_is_reported_in_minutes_not_seconds() -> None:
    assert fact_candidates(PAYLOAD)["duration-minutes"] == (24, "number")


def test_an_empty_end_date_contributes_no_fact() -> None:
    assert "end-date" not in fact_candidates(PAYLOAD)


def test_a_missing_broadcast_contributes_no_timezone() -> None:
    facts = fact_candidates({"id": 4, "num_episodes": 1})
    assert "broadcast-timezone" not in facts


def test_a_boolean_is_typed_as_boolean() -> None:
    from api.worker import mal_import

    original = mal_import.fact_candidates
    facts = original({"id": 5, "mean": True})
    assert facts["mal-score"] == (True, "boolean")


def test_subject_types_fall_back_to_other() -> None:
    assert work_type_for("anime") == "anime"
    assert work_type_for("galgame") == "galgame"
    assert work_type_for("not-a-type") == "other"
    assert work_type_for(None) == "other"
