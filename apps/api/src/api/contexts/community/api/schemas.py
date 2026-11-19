from pydantic import BaseModel, ConfigDict, Field


class RelationshipReason(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, coerce_numbers_to_str=True)

    reason: str = Field(default="", max_length=256)
