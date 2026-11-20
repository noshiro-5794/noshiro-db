from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import TypeAdapter, ValidationError

from api.contexts.access.dependencies import current_user
from api.contexts.community.notifications import (
    list_for_user,
    mark_all_read,
    read_one,
    unread_count,
)
from api.db import SessionDep
from api.shared.cursor import decode
from api.shared.pagination import PageSize, cursor_payload
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/community", tags=["community"])


@router.get("/me/notifications/unread-count/")
async def notification_unread_count(
    session: SessionDep, user: Annotated[Any, Depends(current_user)]
) -> dict[str, int]:
    return {"unread_count": await unread_count(session, user_id=user.id)}


@router.put("/me/notifications/read-state/")
async def notification_read_all(
    session: SessionDep, user: Annotated[Any, Depends(current_user)]
) -> dict[str, int]:
    return {"updated_count": await mark_all_read(session, user_id=user.id)}


@router.put("/me/notifications/{notification_id}/read-state/")
async def notification_read(
    notification_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await read_one(session, user_id=user.id, notification_id=notification_id)
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Notification not found.",
            code="community.notification_not_found",
        ) from error


@router.get("/me/notifications/")
async def notification_list(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
    cursor: str = "",
    page_size: PageSize = 16,
    is_read: str | None = None,
) -> dict[str, Any]:
    parsed = decode(cursor or None)
    read_filter = False if is_read is None else None
    if is_read:
        try:
            read_filter = TypeAdapter(bool).validate_python(is_read)
        except ValidationError as error:
            raise ProblemError(
                status_code=400,
                detail="Request validation failed.",
                errors={"is_read": ["Must be a valid boolean."]},
            ) from error
    results, next_cursor, previous_cursor = await list_for_user(
        session,
        user_id=user.id,
        cursor=parsed,
        page_size=page_size,
        is_read=read_filter,
    )
    return cursor_payload(
        request, results=results, next_cursor=next_cursor, previous_cursor=previous_cursor
    )
