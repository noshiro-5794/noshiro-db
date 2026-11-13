"""The redirect walk the identity reconciliation depends on."""

from __future__ import annotations

from api.worker.mal_identity import Discovery, resolve_with


def test_a_chain_resolves_to_its_root() -> None:
    assert resolve_with({"a": "b", "b": "c"}, "a") == "c"


def test_a_dangling_source_resolves_to_itself() -> None:
    assert resolve_with({}, "a") == "a"


def test_a_cycle_returns_the_original_instead_of_looping() -> None:
    assert resolve_with({"a": "b", "b": "a"}, "a") == "a"


def test_the_summary_reports_only_the_discovery_counters() -> None:
    summary = Discovery(
        mal_entities=3, examined=3, anilist_matches=2, skipped_redirected=1
    ).summary()
    assert summary == {
        "mal_entities": 3,
        "examined": 3,
        "anilist_matches": 2,
        "skipped_redirected": 1,
    }
