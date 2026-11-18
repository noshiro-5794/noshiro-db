"""Evidence-constrained Bangumi selection and multilingual search queries."""

from decimal import Decimal
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

POLICY_VERSION = "bangumi-search-v1"
ATTEMPT_SCOPE = "bangumi-link:v1"
MIN_CONFIDENCE = Decimal("0.9200")
MAX_SEARCH_QUERIES = 3
SEARCH_LIMIT = 8


class LinkDecision(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    decision: Literal["found", "not_found"]
    subject_id: int | None = None
    confidence: Decimal = Field(ge=0, le=1)
    reason: str = ""

    @field_validator("subject_id", mode="before")
    @classmethod
    def subject_identifier(cls, value: Any) -> int | None:
        return int(value) if value is not None and not isinstance(value, bool) else None

    @field_validator("reason", mode="before")
    @classmethod
    def normalized_reason(cls, value: Any) -> str:
        return str(value or "").strip()[:2000]

    def constrained(self, allowed_ids: set[int]) -> Self:
        if self.decision == "found" and self.subject_id not in allowed_ids:
            return self.model_copy(
                update={"decision": "not_found", "subject_id": None, "confidence": Decimal(0)}
            )
        if self.decision == "not_found":
            return self.model_copy(update={"subject_id": None})
        return self


def name_script(name: str) -> str:
    if any("\u3040" <= char <= "\u30ff" for char in name):
        return "kana"
    if any("\u3400" <= char <= "\u9fff" for char in name):
        return "han"
    if any(char.isascii() and char.isalpha() for char in name):
        return "latin"
    return "other"


def search_queries(names: list[str]) -> list[str]:
    queries = []
    for script in ("kana", "latin", "han"):
        for name in names:
            if name not in queries and name_script(name) == script:
                queries.append(name)
                break
    for name in names:
        if len(queries) >= MAX_SEARCH_QUERIES:
            break
        if name not in queries:
            queries.append(name)
    return queries[:MAX_SEARCH_QUERIES]
