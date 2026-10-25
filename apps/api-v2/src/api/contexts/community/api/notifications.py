from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from api.contexts.access.dependencies import current_user
from api.contexts.community.notifications import (
    list_for_user,
    mark_all_read,
    read_one,
    unread_count,
)
from api.db import SessionDep
from api.shared.cursor import decode, encode
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
    page_size: int = 16,
    is_read: str = "",
) -> dict[str, Any]:
    parsed = decode(cursor or None)
    size = min(max(page_size, 1), 64)
    unread_only = is_read.lower() == "false"
    if is_read.lower() == "true":
        unread_only = False
    results, next_cursor = await list_for_user(
        session,
        user_id=user.id,
        cursor=parsed,
        page_size=size,
        unread_only=unread_only,
    )
    return {
        "next": (
            str(request.url.include_query_params(cursor=encode(next_cursor)))
            if next_cursor is not None
            else None
        ),
        "previous": None,
        "results": results,
    }
