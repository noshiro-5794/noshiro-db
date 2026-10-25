"""The signed-in user's tag names."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user
from api.contexts.library.tags import create_tag, list_tags
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/users", tags=["library"])

BLANK = "This field may not be blank."
TOO_LONG = "Ensure this field has no more than 64 characters."


@router.get("/me/tags/")
async def tags(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_tags(session, user_id=user.id, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.post("/me/tags/")
async def add_tag(
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    name = body.get("name")
    if not isinstance(name, str):
        raise ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors={"name": ["Not a valid string."]},
        )
    name = name.strip()
    if not name:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors={"name": [BLANK]}
        )
    if len(name) > 64:
        raise ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors={"name": [TOO_LONG]},
        )
    data, created = await create_tag(session, user_id=user.id, name=name)
    return JSONResponse(data, status_code=201 if created else 200)
