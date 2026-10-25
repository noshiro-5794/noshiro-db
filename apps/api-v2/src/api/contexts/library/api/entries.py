"""The signed-in user's library."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user
from api.contexts.library.entries import (
    create_entry,
    delete_entry,
    entry_tags,
    get_entry,
    list_entries,
    patch_entry,
    rating_details,
    replace_rating_details,
    replace_tags,
)
from api.contexts.library.releases import delete_state, put_state
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


@router.put("/me/library/entries/{entry_id}/releases/{release_id}/")
async def set_release_state(
    entry_id: int,
    release_id: str,
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data, created = await put_state(
            session,
            user_id=user.id,
            entry_id=entry_id,
            release_id=release_id,
            values=body,
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error
    except FileNotFoundError as error:
        raise ProblemError(status_code=404, detail="Release not found for this Work.") from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201 if created else 200)


@router.delete("/me/library/entries/{entry_id}/releases/{release_id}/", status_code=204)
async def clear_release_state(
    entry_id: int,
    release_id: str,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> None:
    try:
        await delete_state(session, user_id=user.id, entry_id=entry_id, release_id=release_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error
    except FileNotFoundError as error:
        raise ProblemError(status_code=404, detail="Release state not found.") from error


@router.get("/me/library/entries/{entry_id}/tags/")
async def get_entry_tags(
    entry_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> list[dict[str, Any]]:
    return await entry_tags(session, user_id=user.id, entry_id=entry_id)


@router.put("/me/library/entries/{entry_id}/tags/")
async def set_entry_tags(
    entry_id: int,
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> list[dict[str, Any]]:
    try:
        return await replace_tags(session, user_id=user.id, entry_id=entry_id, body=body)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error


@router.get("/me/library/entries/{entry_id}/rating-details/")
async def get_rating_details(
    entry_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> list[dict[str, Any]]:
    return await rating_details(session, user_id=user.id, entry_id=entry_id)


@router.put("/me/library/entries/{entry_id}/rating-details/")
async def set_rating_details(
    entry_id: int,
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> list[dict[str, Any]]:
    try:
        return await replace_rating_details(session, user_id=user.id, entry_id=entry_id, body=body)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
