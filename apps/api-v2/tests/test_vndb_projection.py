from datetime import date

import pytest

from api.worker.vndb_mapping import (
    Name,
    character_facts,
    partial_date,
    positive_int,
    release_facts,
    work_facts,
    work_names,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2024", (date(2024, 1, 1), date(2024, 12, 31), "year")),
        ("2024-02", (date(2024, 2, 1), date(2024, 2, 29), "month")),
        ("2024-02-29", (date(2024, 2, 29), date(2024, 2, 29), "day")),
        ("2023-02-29", (None, None, "unknown")),
        ("TBA", (None, None, "unknown")),
        (None, (None, None, "unknown")),
        ("0000", (None, None, "unknown")),
    ],
)
def test_partial_dates_preserve_precision_and_calendar_bounds(raw, expected):
    assert partial_date(raw) == expected


def test_work_names_preserve_official_original_and_romanized_flags():
    names = work_names(
        {
            "olang": "ja",
            "title": "Title",
            "alttitle": "原題",
            "aliases": ["Alias", None],
            "titles": [{"title": "原題", "lang": "ja", "latin": "Gendai", "official": True}],
        }
    )
    assert names == [
        Name("原題", "ja", "original", True, True),
        Name("Gendai", "ja", "romanized"),
        Name("Alias", "", "alias"),
        Name("Title", "ja", "official", False, True),
        Name("原題", "ja", "original", True, False),
    ]


def test_missing_values_do_not_erase_zero_or_false_facts():
    assert positive_int(True) is None
    assert positive_int(-1) is None
    assert positive_int(0) == 0
    facts = release_facts({"freeware": False, "voiced": 0, "engine": "", "resolution": "1920x1080"})
    assert [(fact.slug, fact.value, fact.value_type) for fact in facts] == [
        ("release-voiced", 0, "number"),
        ("release-freeware", False, "boolean"),
        ("release-resolution", {"value": "1920x1080"}, "json"),
    ]
    assert work_facts({"released": "TBA"})[0].value["raw_value"] == "TBA"


def test_character_actual_sex_retains_spoiler_and_precise_evidence_pointer():
    facts = character_facts({"sex": ["f", "m"], "gender": None})
    assert [(fact.slug, fact.value, fact.json_pointer, fact.spoiler_level) for fact in facts] == [
        ("character-sex", "f", "/sex/0", 0),
        ("character-actual-sex", "m", "/sex/1", 2),
    ]
