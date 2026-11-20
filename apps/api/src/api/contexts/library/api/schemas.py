from typing import Annotated, Literal, cast
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError


class ReviewListQuery(BaseModel):
    keyword: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    ordering: Literal["created_at", "-created_at", "id", "-id"] = "-created_at"


class ReviewCreate(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
    content: str = Field(min_length=1, max_length=20000)
    is_public: bool = True
    is_spoiler: bool = False

    @field_validator("content")
    @classmethod
    def meaningful_content(cls, value: str) -> str:
        if not value.strip():
            raise PydanticCustomError("blank", "UserReview content can not be blank.")
        return value


class ReviewUpdate(ReviewCreate):
    # Omitted PATCH fields use unchecked defaults. Supplied nulls still fail validation.
    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)
    ] = cast(str, None)
    content: str = Field(default=cast(str, None), min_length=1, max_length=20000)
    is_public: bool = cast(bool, None)
    is_spoiler: bool = cast(bool, None)

    @model_validator(mode="after")
    def changed_fields(self) -> "ReviewUpdate":
        if not self.model_fields_set.intersection(type(self).model_fields):
            raise PydanticCustomError("no_fields", "No fields to update.")
        return self


class PublicLibraryQuery(BaseModel):
    status: Literal["doing", "wish", "done", "on_hold", "drop"] | None = None
    subject_type: (
        Literal["anime", "galgame", "manga", "novel", "game", "music", "other", "unclassified"]
        | None
    ) = None
    keyword: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    ordering: Literal[
        "-id",
        "id",
        "-rating",
        "rating",
        "-simple_rating",
        "simple_rating",
        "-watch_end_date",
        "watch_end_date",
        "-watch_start_date",
        "watch_start_date",
    ] = "-id"


class EpisodeProgressReplace(BaseModel):
    finished_episode_ids: list[UUID] = Field(max_length=5000)

    @field_validator("finished_episode_ids")
    @classmethod
    def unique_episodes(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))
