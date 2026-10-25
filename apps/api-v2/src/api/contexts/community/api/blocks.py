from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user
from api.contexts.community.relationships import (
    block_user,
    list_blocks,
    list_mutes,
    unblock_user,
)
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/community", tags=["community"])


def _payload(data: Any) -> dict[str, Any]:
    return data if isinstance(data, dict) else {}


@router.get("/me/blocks/")
async def blocks(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_blocks(session, user_id=user.id, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/me/mutes/")
async def mutes(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_mutes(session, user_id=user.id, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.put("/me/blocks/{target_user_id}/")
async def block(
    target_user_id: int,
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    if target_user_id == user.id:
        raise ProblemError(
            status_code=400,
            detail="can not block yourself",
            code="community.cannot_block_self",
        )
    reason = str(body.get("reason") or "")
    try:
        data, created = await block_user(
            session, user_id=user.id, target_user_id=target_user_id, reason=reason
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="User not found.") from error
    return JSONResponse(data, status_code=201 if created else 200)


@router.delete("/me/blocks/{target_user_id}/", status_code=204)
async def unblock(
    target_user_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> Response:
    try:
        await unblock_user(session, user_id=user.id, target_user_id=target_user_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="User not found.") from error
    return Response(status_code=204)
