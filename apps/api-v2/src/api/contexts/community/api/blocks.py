from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user
from api.contexts.community.relationships import block_user, unblock_user
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/community", tags=["community"])


def _payload(data: Any) -> dict[str, Any]:
    return data if isinstance(data, dict) else {}


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
