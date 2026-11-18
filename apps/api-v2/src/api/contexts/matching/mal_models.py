"""Evidence-constrained output for agent-based MyAnimeList recall."""

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

POLICY_VERSION = "mal-agent-recall-v1"
ATTEMPT_SCOPE = "mal-recall:v1"
MIN_CONFIDENCE = 0.92
TOOL_NAMES = ["knowledge.search_entities", "knowledge.get_entity", "mal.search_anime"]


class RecallDecision(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    decision: Literal["found", "not_found", "matched"]
    mal_id: int | None = Field(default=None, gt=0)
    confidence: float = Field(default=0, ge=0, le=1)
    reason: str = ""

    @field_validator("mal_id", mode="before")
    @classmethod
    def identifier(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("MAL identifiers must be positive integers.")
        return value

    @model_validator(mode="after")
    def normalize(self) -> Self:
        if self.decision == "matched":
            self.decision = "found"
        return self


def observed_mal_ids(tool_name: str, payload: dict[str, Any]) -> set[int]:
    """Extract source identifiers only from the documented tool result fields."""
    values: list[Any] = []
    if tool_name == "mal.search_anime":
        values.extend(
            item.get("id") for item in payload.get("results", []) if isinstance(item, dict)
        )
    elif tool_name == "knowledge.get_entity":
        entity = payload.get("entity") or {}
        values.extend(
            source.get("external_id")
            for source in entity.get("sources", [])
            if isinstance(source, dict)
            and source.get("provider") == "mal"
            and source.get("namespace") == "anime"
        )
    result = set()
    for value in values:
        if isinstance(value, bool):
            continue
        if str(value).isdigit() and int(value) > 0:
            result.add(int(value))
    return result
