from datetime import UTC, datetime
from decimal import Decimal

from api.contexts.signal.domain import MetricRow


def test_value_is_a_number_like_drf_renders_it() -> None:
    row = MetricRow(
        metric="score",
        value=Decimal("7.9"),
        sample_size=12,
        observed_at=datetime(2026, 10, 22, 18, 58, 45, tzinfo=UTC),
        provider="mal",
    )

    assert row.as_payload()["value"] == 7.9


def test_timestamp_ends_with_z_like_drf_renders_it() -> None:
    row = MetricRow(
        metric="rank",
        value=Decimal("1"),
        sample_size=None,
        observed_at=datetime(2026, 10, 22, 18, 58, 45, 123456, tzinfo=UTC),
        provider="anilist",
    )

    assert row.as_payload()["observed_at"] == "2026-10-22T18:58:45.123456Z"
