"""The signed-in user's library."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user
from api.contexts.library.entries import (
    create_entry,
    delete_entry,
    get_entry,
    list_entries,
    patch_entry,
)
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

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


@router.get("/me/library/entries/{entry_id}/")
async def entry(
    entry_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await get_entry(session, user_id=user.id, entry_id=entry_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error


@router.delete("/me/library/entries/{entry_id}/", status_code=204)
async def remove_entry(
    entry_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> None:
    try:
        await delete_entry(session, user_id=user.id, entry_id=entry_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error


@router.patch("/me/library/entries/{entry_id}/")
async def update_entry(
    entry_id: int,
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await patch_entry(session, user_id=user.id, entry_id=entry_id, values=body)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error


@router.post("/me/library/entries/")
async def add_entry(
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data, created = await create_entry(session, user_id=user.id, values=dict(body))
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201 if created else 200)
