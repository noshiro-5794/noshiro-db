"""The fact identity rules, which decide whether two observations agree."""

from __future__ import annotations

from api.worker.facts import PredicateConflict, value_hash


def test_equal_values_share_a_hash_regardless_of_key_order() -> None:
    assert value_hash({"a": 1, "b": 2}) == value_hash({"b": 2, "a": 1})


def test_different_values_produce_different_hashes() -> None:
    assert value_hash(12) != value_hash(13)


def test_a_number_and_its_string_are_not_the_same_fact() -> None:
    assert value_hash(12) != value_hash("12")


def test_predicate_conflicts_are_a_value_error() -> None:
    assert issubclass(PredicateConflict, ValueError)
