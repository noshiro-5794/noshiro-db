"""Record and revision rules that can be checked without a database."""

from __future__ import annotations

from api.worker.records import (
    LEGACY,
    RAW,
    SLIM,
    STUB,
    payload_hash,
    raw_state_for_namespace,
    stub_state_for_namespace,
)


def test_payload_hash_ignores_key_order() -> None:
    assert payload_hash({"a": 1, "b": [2, 3]}) == payload_hash({"b": [2, 3], "a": 1})


def test_payload_hash_changes_with_the_body() -> None:
    assert payload_hash({"a": 1}) != payload_hash({"a": 1, "extra": True})


def test_a_bounded_projection_is_recorded_as_slim() -> None:
    assert raw_state_for_namespace(provider_slug="anilist", namespace_slug="calendar") == SLIM
    assert raw_state_for_namespace(provider_slug="vndb", namespace_slug="vn-related") == SLIM


def test_a_full_object_is_recorded_as_raw() -> None:
    assert raw_state_for_namespace(provider_slug="vndb", namespace_slug="vn") == RAW
    assert raw_state_for_namespace(provider_slug="mal", namespace_slug="anime") == RAW


def test_a_record_without_payload_is_a_stub_except_for_bangumi() -> None:
    assert stub_state_for_namespace(provider_slug="mal") == STUB
    assert stub_state_for_namespace(provider_slug="bangumi") == LEGACY
