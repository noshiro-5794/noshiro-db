"""Validated work classification outputs."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

Confidence = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]


class Classification(BaseModel):
    work_type: Literal[
        "anime", "galgame", "manga", "novel", "game", "music", "other", "unclassified", "abstain"
    ]
    confidence: Confidence
    reason: str

    @field_validator("confidence", mode="before")
    @classmethod
    def numeric_confidence(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("Confidence must be numeric.")
        return value

    @field_validator("reason")
    @classmethod
    def reason_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reason is required.")
        return value.strip()[:2000]
