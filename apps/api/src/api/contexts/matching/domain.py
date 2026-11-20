"""Validated model proposals and automatic binding criteria."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from api.contexts.identity.work_families import are_bindable


class MatchProposal(BaseModel):
    decision: Literal["bind", "group", "reject", "abstain"]
    confidence: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    reason: str

    @field_validator("confidence", mode="before")
    @classmethod
    def reject_boolean_confidence(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("Confidence must be numeric.")
        return value

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reason must not be empty.")
        return value.strip()[:2000]


def structured_sides(left_id: Any, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    row = next((item for item in evidence if item["evidence_type"] == "work_attributes"), None)
    if row is None or not isinstance(row.get("value"), dict):
        return {}
    value = row["value"]
    source, target = value.get("source"), value.get("target")
    if value.get("target_entity_id") and str(value["target_entity_id"]) == str(left_id):
        source, target = target, source
    return {"left": source, "right": target, "comparison": value.get("comparison")}


def bind_allowed(
    *,
    proposal: MatchProposal,
    candidate: Any,
    policy: Any,
    evidence_types: int,
    left_kind: str,
    right_kind: str,
    left_types: set[str],
    right_types: set[str],
    library_conflict: bool,
) -> bool:
    return all(
        (
            proposal.decision == "bind",
            proposal.confidence >= policy.minimum_score,
            candidate.score >= policy.minimum_score,
            candidate.runner_up_margin >= policy.minimum_margin,
            evidence_types >= policy.minimum_evidence_types,
            left_kind == right_kind,
            are_bindable(left_types, right_types),
            not candidate.hard_conflicts,
            not library_conflict,
        )
    )
