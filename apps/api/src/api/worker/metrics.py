"""Engagement numbers, on the one time series every provider shares.

Ported from `record_metrics`. A value that cannot be read as a number is skipped rather
than failing the import: a missing metric must not cost the whole record.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


def as_decimal(raw: Any) -> Decimal | None:
    if raw is None or raw == "" or isinstance(raw, bool):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None


async def record_metrics(
    session: AsyncSession,
    *,
    entity_id: Any,
    provider_record_id: Any,
    observed_at: datetime,
    values: dict[str, Any],
) -> int:
    """Upsert one row per metric, keyed by record, metric and observation time."""
    written = 0
    for metric, raw in values.items():
        value = as_decimal(raw)
        if value is None:
            continue
        await fetch(
            session,
            """
            INSERT INTO metric_snapshot
              (metric, value, sample_size, observed_at, entity_id, provider_record_id)
            VALUES (:metric, :value, NULL, :at, :entity, :record)
            ON CONFLICT (provider_record_id, metric, observed_at)
            DO UPDATE SET value = EXCLUDED.value
            RETURNING id
            """,
            {
                "metric": metric,
                "value": value,
                "at": observed_at,
                "entity": entity_id,
                "record": provider_record_id,
            },
        )
        written += 1
    return written


__all__ = ["as_decimal", "record_metrics"]
