"""Validated weekly slots and timezone-aware occurrence calculation."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator


class SlotProposal(BaseModel):
    decision: Literal["accept", "abstain"]
    weekday: Annotated[int, Field(strict=True, ge=1, le=7)] | None = None
    time: str | None = None
    timezone: str = "Asia/Tokyo"
    duration_minutes: Annotated[int, Field(strict=True, gt=0)] | None = None
    confidence: Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)] = Decimal(0)
    reason: str = ""

    @field_serializer("confidence", when_used="json")
    def confidence_number(self, value: Decimal) -> float:
        return float(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def numeric_confidence(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("Confidence must be numeric.")
        return value

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        value = value or "Asia/Tokyo"
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Unknown timezone.") from error
        return value

    @model_validator(mode="after")
    def accepted_slot_is_complete(self) -> SlotProposal:
        if self.decision == "accept":
            if self.weekday is None or self.time is None:
                raise ValueError("Accepted slot requires a weekday and HH:MM time.")
            if len(self.time) != 5 or self.time[2] != ":":
                raise ValueError("Accepted slot requires HH:MM time.")
            time.fromisoformat(self.time)
        return self

    def next_occurrence(self, now: datetime) -> datetime:
        if self.decision != "accept" or self.weekday is None or self.time is None:
            raise ValueError("An abstention has no broadcast occurrence.")
        zone = ZoneInfo(self.timezone)
        local = now.astimezone(zone)
        day = local.date() + timedelta(days=(self.weekday - local.isoweekday()) % 7)
        slot = datetime.combine(day, time.fromisoformat(self.time), tzinfo=zone)
        if slot <= local:
            slot += timedelta(days=7)
        return slot.astimezone(UTC)
