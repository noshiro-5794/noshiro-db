from typing import Annotated, Any

from fastapi import APIRouter, Depends

from api.contexts.access.dependencies import current_user
from api.contexts.community.notifications import (
    mark_all_read,
    read_one,
    unread_count,
)
from api.db import SessionDep
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
