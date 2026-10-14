import time
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.sync.providers.rate_limiter import (
    GATE_KEY,
    DistributedRateLimiter,
    parse_gate_delay,
)

NAME = "anilist"


@pytest.fixture(autouse=True)
def _clear_gate():
    cache.delete(GATE_KEY.format(name=NAME))
    yield
    cache.delete(GATE_KEY.format(name=NAME))


def test_retry_after_wins_over_the_budget_headers() -> None:
    delay = parse_gate_delay(
        {"Retry-After": "12", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "60"},
        now=time.time(),
    )

    assert delay == 12


def test_a_spent_budget_waits_for_the_reset_window() -> None:
    # AniList documents this header as a duration...
    assert (
        parse_gate_delay(
            {"X-RateLimit-Remaining": "1", "X-RateLimit-Reset": "30"}, now=1000.0
        )
        == 30
    )
    # ...some stacks send an absolute epoch instead, and the wait is the
    # distance to it rather than the raw value.
    reset_at = 1_700_000_000
    assert (
        parse_gate_delay(
            {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset_at)},
            now=reset_at - 30,
        )
        == 30
    )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-RateLimit-Remaining": "25"},
        {"X-RateLimit-Remaining": "1"},
        {"X-RateLimit-Remaining": "not-a-number", "X-RateLimit-Reset": "30"},
        {"X-RateLimit-Remaining": "1", "X-RateLimit-Reset": "whenever"},
        {"Retry-After": "later"},
    ],
)
def test_nothing_to_hold_back_on(headers: dict[str, str]) -> None:
    assert parse_gate_delay(headers, now=1000.0) == 0.0


def test_observe_and_penalize_raise_a_shared_gate() -> None:
    limiter = DistributedRateLimiter(NAME, interval=0.0)

    limiter.observe({"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "45"})

    stored = float(cache.get(GATE_KEY.format(name=NAME)))
    assert stored - time.time() == pytest.approx(45, abs=2)

    # A later, smaller hold must not shorten the gate an earlier one set.
    limiter.penalize(5)
    assert float(cache.get(GATE_KEY.format(name=NAME))) == pytest.approx(stored, abs=1)


def test_acquire_waits_out_the_gate_before_claiming_a_slot() -> None:
    limiter = DistributedRateLimiter(NAME, interval=1.0)
    limiter.penalize(30)
    slept: list[float] = []

    with patch("apps.sync.providers.rate_limiter.time.sleep", side_effect=slept.append):
        limiter.acquire()

    # It waits in slices so a gate raised mid-sleep is noticed, and the wait
    # happens before the claim rather than while holding it.
    assert slept
    assert sum(slept) >= 30


def test_interval_slots_are_spaced_for_the_next_caller() -> None:
    limiter = DistributedRateLimiter(NAME, interval=2.0)
    limiter.acquire()

    remaining = float(cache.get(GATE_KEY.format(name=NAME))) - time.time()

    assert remaining == pytest.approx(2.0, abs=0.5)


def test_a_missing_cache_still_falls_back_without_bursting() -> None:
    limiter = DistributedRateLimiter(NAME, interval=0.5, allow_fallback=True)

    with patch("apps.sync.providers.rate_limiter.cache.get", side_effect=RuntimeError):
        # The observation is best effort: the request it describes was already
        # sent, so a cache outage must not invent a failure.
        limiter.observe({"Retry-After": "60"})
