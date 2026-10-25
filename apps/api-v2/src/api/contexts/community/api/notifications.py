from typing import Annotated, Any

from fastapi import APIRouter, Depends

from api.contexts.access.dependencies import current_user
from api.contexts.community.notifications import mark_all_read, unread_count
from api.db import SessionDep

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
