from typing import Annotated, Any, Literal, cast

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError


class RelationshipReason(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, coerce_numbers_to_str=True)

    reason: str = Field(default="", max_length=256)


def _comment_text(value: str) -> str:
    if not value.strip():
        raise PydanticCustomError("blank", "Comment content can not be blank.")
    return value


CommentText = Annotated[
    str, StringConstraints(min_length=1, max_length=5000), AfterValidator(_comment_text)
]
Visibility = Literal["public", "private", "followers"]


class CommentTarget(BaseModel):
    target_type: Literal["post", "review", "collection", "activity"]
    target_id: int = Field(ge=1, le=2**63 - 1)

    @field_validator("target_id", mode="before")
    @classmethod
    def integer_target(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise PydanticCustomError("int_type", "A valid integer is required.")
        return value


class CommentCreate(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    content: CommentText
    parent_id: int = Field(default=cast(int, None), le=2**63 - 1)
    visibility: Visibility = "public"
    is_spoiler: bool = False

    @field_validator("parent_id", mode="before")
    @classmethod
    def integer_parent(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise PydanticCustomError("int_type", "A valid integer is required.")
        return value


class TargetCommentCreate(CommentCreate, CommentTarget):
    pass


class CommentUpdate(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    # Supplied nulls fail validation while omitted PATCH fields remain unset.
    content: CommentText = cast(str, None)
    visibility: Visibility = cast(Visibility, None)
    is_spoiler: bool = cast(bool, None)

    @model_validator(mode="after")
    def changed_fields(self) -> "CommentUpdate":
        if not self.model_fields_set:
            raise PydanticCustomError("no_fields", "No fields to update.")
        return self


class CommentModeration(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    action_type: Literal["hide", "lock"]
    reason: str = Field(default="", max_length=1000)
