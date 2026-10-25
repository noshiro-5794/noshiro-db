"""The signed-in user's own collections."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user
from api.contexts.library.collections import (
    create_collection,
    list_public_collections,
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
