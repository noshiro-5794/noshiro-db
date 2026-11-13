"""The frontier walk, against a fake provider.

The interesting behaviour is all in the stopping rules, and none of it needs a network or
a database to exercise.
"""

from __future__ import annotations

from api.worker.frontier import Frontier, ProviderError, walk

START = Frontier(highest_existing_id=100, probed_to=100, seed=100)


def exists_up_to(highest: int):
    def fetch(value: int) -> dict[str, int]:
        if value > highest:
            raise ProviderError("not found", is_not_found=True)
        return {"id": value}

    return fetch


def test_walk_records_the_highest_id_that_exists() -> None:
    result = walk(exists_up_to(105), start=START, window=50, max_misses=3)
    assert result.highest_existing_id == 105
    assert result.probed_to == 108
    assert result.misses == 3
    assert result.stopped_by == "missing_run"


def test_a_window_ends_the_walk_before_the_frontier() -> None:
    result = walk(exists_up_to(1000), start=START, window=10, max_misses=3)
    assert result.probed == 10
    assert result.stopped_by == "window"
    assert result.highest_existing_id == 110


def test_a_provider_error_is_not_a_miss() -> None:
    def fetch(value: int) -> dict[str, int]:
        if value == 103:
            raise ProviderError("rate limited", is_not_found=False)
        return {"id": value}

    result = walk(fetch, start=START, window=50, max_misses=3)
    assert result.stopped_by == "provider_error"
    assert result.misses == 0
    assert result.highest_existing_id == 102
    assert result.probed_to == 102, "the failing id is not recorded as probed"


def test_an_unexpected_error_also_stops_without_a_miss() -> None:
    def fetch(value: int) -> dict[str, int]:
        if value > 101:
            raise RuntimeError("connection reset")
        return {"id": value}

    result = walk(fetch, start=START, window=50, max_misses=3)
    assert result.stopped_by == "unexpected_error"
    assert result.misses == 0
    assert result.highest_existing_id == 101


def test_a_missing_run_stops_at_the_first_miss_limit() -> None:
    result = walk(exists_up_to(100), start=START, window=100, max_misses=5)
    assert result.probed == 5
    assert result.misses == 5
    assert result.probed_to == 105
    assert result.highest_existing_id == 100


def test_gaps_inside_the_space_do_not_look_like_the_end() -> None:
    def fetch(value: int) -> dict[str, int]:
        if value in (102, 104):
            raise ProviderError("not found", is_not_found=True)
        if value > 106:
            raise ProviderError("not found", is_not_found=True)
        return {"id": value}

    result = walk(fetch, start=START, window=50, max_misses=2)
    assert result.highest_existing_id == 106
    assert result.stopped_by == "missing_run"


def test_a_failure_on_the_last_allowed_probe_keeps_its_reason() -> None:
    def fetch(value: int) -> dict[str, int]:
        if value == 102:
            raise ProviderError("rate limited", is_not_found=False)
        return {"id": value}

    result = walk(fetch, start=START, window=2, max_misses=3)
    assert result.probed == 2
    assert result.stopped_by == "provider_error"
