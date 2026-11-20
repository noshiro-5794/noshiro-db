"""Typed classification and evidence extraction outputs."""

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


class EvidenceClaim(BaseModel):
    predicate: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=128)]
    value: Any = None
    value_type: Literal["string", "number", "boolean", "date", "entity", "json"]
    language: Annotated[str, Field(max_length=35)] = ""
    spoiler_level: Annotated[int, Field(strict=True, ge=0, le=3)] = 0
    safety: Literal["safe", "suggestive", "explicit", "unknown"] = "unknown"
    json_pointer: str
    confidence: Confidence

    @field_validator("confidence", mode="before")
    @classmethod
    def numeric_confidence(cls, value: Any) -> Any:
        return Classification.numeric_confidence(value)

    @field_validator("json_pointer")
    @classmethod
    def pointer_required(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("JSON pointer must start with /.")
        return value[:512]


class Extraction(BaseModel):
    claims: Annotated[list[EvidenceClaim], Field(max_length=100)]

    @property
    def confidence(self) -> Decimal:
        return min((claim.confidence for claim in self.claims), default=Decimal(0))
