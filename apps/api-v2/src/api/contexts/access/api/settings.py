"""The signed-in user's display preferences.

Separate from the profile write because settings accept a different field set and
gate adult content behind an explicit confirmation. The response is the whole
profile, so a client can replace its cached copy instead of merging a patch.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from api.contexts.access.api.profile import (
    COLOR,
    DEFAULT_THEME,
    INVALID_COLOR,
    profile_payload,
    profile_row,
)
from api.contexts.access.dependencies import current_user
from api.contexts.presentation.fragments import fetch
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/users", tags=["profile"])

LANGUAGE_CHOICES: tuple[str, ...] = ("auto", "en-US", "zh-CN", "ja-JP")
APPEARANCE_CHOICES: tuple[str, ...] = ("auto", "light", "dark")

NULL = "This field may not be null."
INVALID_BOOLEAN = "Must be a valid boolean."
NO_FIELDS = "No fields to update."
CONFIRM_REQUIRED = "Explicit confirmation is required to enable adult content."

TRUE_VALUES: frozenset[Any] = frozenset({"t", "y", "yes", "true", "on", "1", 1})
FALSE_VALUES: frozenset[Any] = frozenset({"f", "n", "no", "false", "off", "0", 0})


def _boolean(value: Any) -> bool | None:
    """Coerce the spellings DRF's boolean field accepts; None means it is not one."""
    if isinstance(value, str):
        value = value.lower()
    try:
        if value in TRUE_VALUES:
            return True
        if value in FALSE_VALUES:
            return False
    except TypeError:
        return None
    return None


def _validate(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """The same rules and messages the Django serializer answers with."""
    values: dict[str, Any] = {}
    errors: dict[str, list[str]] = {}
    for field, choices in (
        ("language", LANGUAGE_CHOICES),
        ("appearance", APPEARANCE_CHOICES),
    ):
        if field not in payload:
            continue
        value = payload[field]
        if value is None:
            errors[field] = [NULL]
        elif str(value) not in choices:
            errors[field] = [f'"{value}" is not a valid choice.']
        else:
            values[field] = str(value)
    if "theme_color" in payload:
        color = payload["theme_color"]
        if color is None:
            errors["theme_color"] = [NULL]
        elif isinstance(color, bool) or not isinstance(color, (str, int, float)):
            errors["theme_color"] = [INVALID_COLOR]
        else:
            text = str(color).strip()
            if not text:
                values["theme_color"] = DEFAULT_THEME
            elif not COLOR.match(text):
                errors["theme_color"] = [INVALID_COLOR]
            else:
                values["theme_color"] = text
    for field in ("show_adult_content", "confirm_adult_content"):
        if field not in payload:
            continue
        value = payload[field]
        if value is None:
            errors[field] = [NULL]
        else:
            boolean = _boolean(value)
            if boolean is None:
                errors[field] = [INVALID_BOOLEAN]
            else:
                values[field] = boolean
    if errors:
        return values, errors
    if not values:
        errors["non_field_errors"] = [NO_FIELDS]
        return values, errors
    if values.get("show_adult_content") and not values.get("confirm_adult_content"):
        errors["confirm_adult_content"] = [CONFIRM_REQUIRED]
        return values, errors
    values.pop("confirm_adult_content", None)
    return values, errors


@router.get("/me/settings/")
async def my_settings(
    session: SessionDep, user: Annotated[Any, Depends(current_user)]
) -> dict[str, Any]:
    return profile_payload(await profile_row(session, user), user)


@router.patch("/me/settings/")
async def update_settings(
    payload: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    values, errors = _validate(payload)
    if errors:
        raise ProblemError(status_code=400, detail="Request validation failed.", errors=errors)
    profile = await profile_row(session, user)
    if not values:
        return profile_payload(profile, user)
    assignments = ", ".join(f"{column} = :{column}" for column in values)
    if values.get("show_adult_content"):
        assignments += ", adult_content_confirmed_at = now()"
    async with session.begin_nested():
        rows = await fetch(
            session,
            f"UPDATE user_profile SET {assignments} WHERE user_id = :user_id"
            " RETURNING nickname, bio, avatar, language, appearance, theme_color,"
            " show_adult_content, adult_content_confirmed_at",
            {**values, "user_id": user.id},
        )
    await session.commit()
    return profile_payload(rows[0] if rows else profile, user)
