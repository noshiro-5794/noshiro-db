"""Metric rows as the API renders them.

The Django service renders DRF decimals as fixed-point strings with six places,
and timestamps as ISO 8601 with a ``Z`` suffix. The replacement has to match that
byte for byte, so the conversion lives here rather than in the router.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MetricRow:
    metric: str
    value: Decimal
    sample_size: int | None
    observed_at: datetime
    provider: str

    def as_payload(self) -> dict[str, object]:
        return {
            "metric": self.metric,
            # The Django service renders this through DRF's JSON encoder, which
            # turns a Decimal into a float. The OpenAPI snapshot says "string",
            # so the contract and the implementation disagree; parity copies the
            # implementation first and the disagreement is recorded for a
            # deliberate fix on both sides later.
            "value": float(self.value),
            "sample_size": self.sample_size,
            "observed_at": _isoformat(self.observed_at),
            "provider": self.provider,
        }


def _isoformat(value: datetime) -> str:
    text = value.astimezone(UTC).isoformat()
    return text[:-6] + "Z" if text.endswith("+00:00") else text
