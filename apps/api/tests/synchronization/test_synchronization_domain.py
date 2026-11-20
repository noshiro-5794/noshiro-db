from datetime import UTC, datetime, timedelta

import pytest

from api.contexts.synchronization.domain import TRANSITIONS, classify_failure
from api.integrations.providers.errors import ProviderError

NOW = datetime(2026, 11, 16, tzinfo=UTC)


def test_campaign_phases_advance_in_order():
    assert ("queued", "discovering") in TRANSITIONS
    assert ("reviewing", "completed") in TRANSITIONS
    assert ("fetching", "failed") in TRANSITIONS
    assert ("paused", "fetching") in TRANSITIONS
    assert ("fetching", "completed") not in TRANSITIONS
    assert ("completed", "fetching") not in TRANSITIONS


@pytest.mark.parametrize(
    "status,attempt,expected",
    [
        (404, 1, "skipped"),
        (429, 1, "queued"),
        (503, 4, "queued"),
        (503, 5, "failed"),
        (401, 1, "failed"),
    ],
)
def test_failure_classification_preserves_retry_budget(status, attempt, expected):
    failure = classify_failure(
        ProviderError("fixture", status_code=status), attempt=attempt, max_attempts=5, now=NOW
    )
    assert failure.status == expected
    assert (failure.next_retry_at is not None) == (expected == "queued")


def test_provider_retry_after_wins_over_exponential_delay():
    failure = classify_failure(
        ProviderError("rate limited", status_code=429, retry_after=120),
        attempt=1,
        max_attempts=5,
        now=NOW,
    )
    assert failure.next_retry_at == NOW + timedelta(seconds=120)
