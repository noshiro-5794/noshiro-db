"""Parsing rules that decide what a payload contributes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from api.worker.metrics import as_decimal
from api.worker.profiles import parse_iso_date


def test_a_provider_date_becomes_a_date() -> None:
    assert parse_iso_date("2026-01-05") == date(2026, 1, 5)


def test_a_longer_timestamp_is_truncated_to_its_date() -> None:
    assert parse_iso_date("2026-01-05T12:00:00Z") == date(2026, 1, 5)


def test_empty_and_malformed_dates_are_ignored() -> None:
    assert parse_iso_date("") is None
    assert parse_iso_date(None) is None
    assert parse_iso_date("not a date") is None
    assert parse_iso_date("2026-13-45") is None


def test_metric_values_are_converted_when_readable() -> None:
    assert as_decimal(1234) == Decimal("1234")
    assert as_decimal("7.5") == Decimal("7.5")


def test_unreadable_metrics_are_skipped_rather_than_raising() -> None:
    assert as_decimal("abc") is None
    assert as_decimal(None) is None
    assert as_decimal("") is None
    assert as_decimal(True) is None, "a boolean is not an engagement number"
