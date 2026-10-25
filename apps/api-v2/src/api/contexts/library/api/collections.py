"""The signed-in user's own collections."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user
from api.contexts.library.collections import (
    add_item,
    create_collection,
    delete_collection,
    list_items,
    list_public_collections,
    my_collection,
    update_collection,
)
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/users", tags=["collections"])


@router.get("/me/collections/")
async def my_collections(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
    keyword: str = "",
    ordering: str = "id",
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_public_collections(
        session,
        viewer_id=user.id,
        user_id=user.id,
        keyword=keyword.strip(),
        ordering=ordering,
        page=page,
        page_size=page_size,
        public_only=False,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.post("/me/collections/")
async def add_collection(
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data = await create_collection(session, user_id=user.id, body=body)
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201)


@router.get("/me/collections/{collection_id}/")
async def one_collection(
    collection_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await my_collection(session, user_id=user.id, collection_id=collection_id)
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="UserCollection not found.",
            code="users.collection_not_found",
        ) from error


@router.patch("/me/collections/{collection_id}/")
async def patch_collection(
    collection_id: int,
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await update_collection(
            session, user_id=user.id, collection_id=collection_id, body=body
        )
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="UserCollection not found.",
            code="users.collection_not_found",
        ) from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error


@router.delete("/me/collections/{collection_id}/", status_code=204)
async def remove_collection(
    collection_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> None:
    try:
        await delete_collection(session, user_id=user.id, collection_id=collection_id)
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="UserCollection not found.",
            code="users.collection_not_found",
        ) from error


@router.get("/me/collections/{collection_id}/items/")
async def collection_items(
    collection_id: int,
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    try:
        total, results = await list_items(
            session,
            viewer_id=user.id,
            user_id=user.id,
            collection_id=collection_id,
            page=page,
            page_size=page_size,
        )
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="UserCollection not found.",
            code="users.collection_not_found",
        ) from error
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.post("/me/collections/{collection_id}/items/")
async def add_collection_item(
    collection_id: int,
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data, created = await add_item(
            session, user_id=user.id, collection_id=collection_id, body=body
        )
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Library entry not found.",
        ) from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201 if created else 200)
