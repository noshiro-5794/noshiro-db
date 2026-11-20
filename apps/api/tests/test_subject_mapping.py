"""The Bangumi subject mapper, where a wrong rule silently changes what a work is."""

from __future__ import annotations

from datetime import date

from api.worker.subject_mapping import (
    infobox_entries,
    map_subject,
    normalize_key,
    subject_date,
    subject_type,
    tag_names,
    work_facts,
)


def test_an_anime_is_type_two() -> None:
    assert subject_type({"type": 2}) == "anime"


def test_a_book_splits_by_platform_string() -> None:
    assert subject_type({"type": 1, "platform": "小说"}) == "novel"
    assert subject_type({"type": 1, "platform": "漫画"}) == "manga"
    assert subject_type({"type": 1, "platform": "其他"}) == "book"


def test_a_game_is_a_galgame_only_with_the_tag() -> None:
    assert subject_type({"type": 4, "meta_tags": ["Galgame"]}) == "galgame"
    assert subject_type({"type": 4, "meta_tags": ["RPG"]}) == "game"
    assert subject_type({"type": 4}) == "game"


def test_an_unknown_or_boolean_type_is_other() -> None:
    assert subject_type({"type": 99}) == "other"
    assert subject_type({"type": True}) == "other"
    assert subject_type({}) == "other"


def test_a_malformed_date_is_absent_rather_than_wrong() -> None:
    assert subject_date({"date": "2020-04-05"}) == date(2020, 4, 5)
    assert subject_date({"date": "2020-13-01"}) is None
    assert subject_date({"date": ""}) is None
    assert subject_date({}) is None


def test_tags_preserve_source_text_and_drop_empty_values() -> None:
    assert tag_names({"meta_tags": ["  Sci-Fi ", "", "DRAMA"]}) == ["Sci-Fi", "DRAMA"]


def test_infobox_values_are_flattened_from_both_shapes() -> None:
    payload = {
        "infobox": [
            {"key": "别名", "value": "Alternative"},
            {"key": "话数", "value": [{"v": "12"}, {"v": "13"}]},
            {"key": "", "value": ""},
        ]
    }
    entries = infobox_entries(payload)
    assert entries[0] == {"key": "别名", "value": ["Alternative"]}
    assert entries[1] == {"key": "话数", "value": ["12", "13"]}
    # An empty string is still a one-element list, and the old service keeps it: only a
    # value that flattens to no elements at all is dropped. Kept for parity.
    assert entries[2] == {"key": "", "value": [""]}
    assert len(entries) == 3


def test_the_mapped_shape_carries_the_expected_fields() -> None:
    mapped = map_subject(
        {
            "type": 2,
            "name": "  Title  ",
            "name_cn": "标题",
            "summary": "Summary",
            "images": {"large": "L", "medium": "M"},
            "total_episodes": 12,
            "nsfw": True,
        }
    )
    assert mapped["title"] == "Title"
    assert mapped["title_cn"] == "标题"
    assert mapped["image_original"] == "L"
    assert mapped["total_episodes"] == 12
    assert mapped["nsfw"] is True
    assert mapped["subject_type"] == "anime"


def test_wrong_types_become_absent_instead_of_coerced() -> None:
    mapped = map_subject({"type": 2, "eps": "12", "series": "yes", "nsfw": 1})
    assert mapped["eps"] is None
    assert mapped["series"] is False
    assert mapped["nsfw"] is False


def test_lookup_keys_collapse_case_and_whitespace() -> None:
    assert normalize_key("  Sci   Fi ") == "sci fi"


def test_facts_keep_their_declared_types() -> None:
    facts = work_facts(
        map_subject(
            {
                "type": 2,
                "date": "2021-04-03",
                "platform": "TV",
                "series": True,
                "total_episodes": 12,
                "meta_tags": ["SF"],
            }
        )
    )
    assert facts["release-date"] == ("2021-04-03", "date")
    assert facts["platform"] == ("TV", "string")
    assert facts["series"] == (True, "boolean")
    assert facts["episode-count"] == (12, "number")
    assert facts["provider-tags"] == (["SF"], "json")


def test_absent_values_contribute_no_fact() -> None:
    facts = work_facts(map_subject({"type": 2}))
    assert "release-date" not in facts
    assert "episode-count" not in facts
    assert "platform" not in facts
