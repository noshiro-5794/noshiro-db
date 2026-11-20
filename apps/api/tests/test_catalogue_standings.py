"""The percentile standing, including the rules that are easy to "fix" by accident.

The shadow comparison against Django matched exactly, so these rules are the contract:
equal reach shares the lower rank, a single sample scores full marks, and the scale is 100.
"""

from __future__ import annotations

from decimal import Decimal

from api.worker.catalogue import _resolve, standings


def test_the_highest_reach_gets_the_full_scale() -> None:
    scores = standings({"a": Decimal(1), "b": Decimal(2), "c": Decimal(3)})
    assert scores["c"] == Decimal(100)
    assert scores["a"] == Decimal(0)


def test_the_lowest_reach_gets_zero() -> None:
    scores = standings({"a": Decimal(1), "b": Decimal(2)})
    assert scores["a"] == 0


def test_equal_reach_shares_the_lower_rank_instead_of_splitting() -> None:
    scores = standings({"a": Decimal(1), "b": Decimal(2), "c": Decimal(2)})
    assert scores["b"] == scores["c"], "equal reach must not be ordered arbitrarily"
    assert scores["b"] == Decimal(50)


def test_a_single_entity_scores_full_marks() -> None:
    assert standings({"only": Decimal(7)}) == {"only": Decimal(100)}


def test_an_empty_series_produces_no_standings() -> None:
    assert standings({}) == {}


def test_the_standing_is_a_ratio_not_a_count() -> None:
    scores = standings({str(i): Decimal(i) for i in range(1, 101)})
    assert max(scores.values()) == Decimal(100)
    assert min(scores.values()) == 0


def test_a_redirect_chain_resolves_to_its_end() -> None:
    redirects = {"a": "b", "b": "c"}
    assert _resolve(redirects, "a") == "c"
    assert _resolve(redirects, "c") == "c"


def test_a_redirect_cycle_falls_back_to_the_original() -> None:
    assert _resolve({"a": "b", "b": "a"}, "a") == "a"
