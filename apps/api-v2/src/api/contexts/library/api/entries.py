"""The signed-in user's library."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from api.contexts.access.dependencies import current_user
from api.contexts.library.entries import list_entries
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload

router = APIRouter(prefix="/api/v1/users", tags=["library"])


@router.get("/me/library/entries/")
async def entries(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
    status: str = "",
    subject_type: str = "",
    keyword: str = "",
    tag_id: int = 0,
    ordering: str = "-updated_at",
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_entries(
        session,
        user_id=user.id,
        status=status,
        subject_type=subject_type,
        keyword=keyword.strip(),
        tag_id=tag_id,
        ordering=ordering,
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)
