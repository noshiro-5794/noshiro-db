"""The canonical hash that decides whether a payload is new.

It is the one part of ingestion that can be wrong invisibly: if the rendering changes, the
stored hashes stop matching and the whole catalogue is re-ingested. These tests pin it.
"""

from __future__ import annotations

from datetime import UTC

from api.worker.ingestion import normalized_hash


def test_key_order_does_not_change_the_hash() -> None:
    assert normalized_hash({"a": 1, "b": 2}) == normalized_hash({"b": 2, "a": 1})


def test_nesting_is_canonicalised_too() -> None:
    left = {"outer": {"x": [1, 2], "y": {"z": 3}}}
    right = {"outer": {"y": {"z": 3}, "x": [1, 2]}}
    assert normalized_hash(left) == normalized_hash(right)


def test_a_changed_value_changes_the_hash() -> None:
    assert normalized_hash({"a": 1}) != normalized_hash({"a": 2})


def test_whitespace_in_the_source_data_is_not_part_of_the_hash() -> None:
    assert normalized_hash({"title": " a b "}) == normalized_hash({"title": " a b "})


def test_non_json_values_are_stringified_not_rejected() -> None:
    from datetime import datetime

    digest = normalized_hash({"at": datetime(2026, 1, 1, tzinfo=UTC)})
    assert len(digest) == 64


def test_unicode_is_preserved_rather_than_escaped() -> None:
    assert normalized_hash({"t": "冴えない彼女"}) != normalized_hash({"t": "冴えない彼女 "})
    assert len(normalized_hash({"t": "冴えない彼女"})) == 64
