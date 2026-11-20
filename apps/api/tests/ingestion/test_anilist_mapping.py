"""The AniList mapper, including the fact the reconciliation depends on."""

from __future__ import annotations

from api.contexts.identity.names import SourceName
from api.worker.anilist_import import _fuzzy_date, fact_candidates, name_entries

MEDIA = {
    "id": 1,
    "idMal": 42,
    "title": {"romaji": "Romaji", "english": "English", "native": "日本語"},
    "startDate": {"year": 2020, "month": 4, "day": 5},
    "endDate": {"year": 2020, "month": 6, "day": None},
    "episodes": 12,
    "duration": 24,
    "format": "TV",
    "status": "FINISHED",
    "season": "SPRING",
    "seasonYear": 2020,
    "averageScore": 81,
    "popularity": 5000,
}


def test_names_keep_the_provider_kinds() -> None:
    assert name_entries(MEDIA) == [
        SourceName("Romaji", "ja", "romanized", is_official=True, script="Latn"),
        SourceName("English", "en", "official", is_official=True, script="Latn"),
        SourceName("日本語", "ja", "original", is_official=True, script="Jpan"),
    ]


def test_an_unknown_day_defaults_to_the_first_of_a_known_month() -> None:
    assert _fuzzy_date({"year": 2020, "month": 6, "day": None}) == "2020-06-01"
    assert _fuzzy_date({"year": 2020, "month": 4, "day": 5}) == "2020-04-05"
    assert _fuzzy_date({}) is None


def test_the_official_mal_id_becomes_a_fact() -> None:
    facts = fact_candidates(MEDIA)
    assert facts["anilist-id-mal"] == (42, "number")


def test_facts_keep_numbers_as_numbers() -> None:
    facts = fact_candidates(MEDIA)
    assert facts["episode-count"] == (12, "number")
    assert "anilist-format" not in facts
    assert facts["anilist-average-score"] == (81, "number")
    assert facts["release-date"] == ("2020-04-05", "date")


def test_absent_fields_contribute_nothing() -> None:
    facts = fact_candidates({"id": 2})
    assert "anilist-id-mal" not in facts
    assert "episode-count" not in facts
