from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user
from api.contexts.community.relationships import (
    block_user,
    follow_user,
    list_blocks,
    list_followers,
    list_following,
    list_mutes,
    unblock_user,
    unfollow_user,
)
from api.contexts.presentation.fragments import fetch
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


@router.put("/me/following/{target_user_id}/")
async def follow(
    target_user_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data, created = await follow_user(
            session, follower_id=user.id, target_user_id=target_user_id
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="User not found.") from error
    except PermissionError as error:
        code = str(error)
        raise ProblemError(
            status_code=400,
            detail={
                "community.cannot_follow_self": "can not follow yourself",
                "community.cannot_follow_blocked_user": "can not follow blocked user",
            }[code],
            code=code,
        ) from error
    return JSONResponse(data, status_code=201 if created else 200)


@router.delete("/me/following/{target_user_id}/", status_code=204)
async def unfollow(
    target_user_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> Response:
    try:
        await unfollow_user(session, follower_id=user.id, target_user_id=target_user_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="User not found.") from error
    return Response(status_code=204)


@router.get("/me/followers/")
async def followers(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_followers(session, user_id=user.id, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/me/following/")
async def following(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_following(session, user_id=user.id, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


async def _ensure_user(session: SessionDep, user_id: int) -> None:
    rows = await fetch(session, 'SELECT 1 FROM "user" WHERE id = :id', {"id": user_id})
    if not rows:
        raise ProblemError(status_code=404, detail="User not found.", code="users.user_not_found")


@router.get("/users/{user_id}/followers/")
async def public_followers(user_id: int, session: SessionDep, request: Request) -> dict[str, Any]:
    await _ensure_user(session, user_id)
    page, page_size = page_params(request)
    total, results = await list_followers(session, user_id=user_id, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/users/{user_id}/following/")
async def public_following(user_id: int, session: SessionDep, request: Request) -> dict[str, Any]:
    await _ensure_user(session, user_id)
    page, page_size = page_params(request)
    total, results = await list_following(session, user_id=user_id, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)
