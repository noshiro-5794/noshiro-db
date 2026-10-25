from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user, optional_user, staff_user
from api.contexts.community.bookmarks import (
    list_bookmarks,
    remove_bookmark,
    set_bookmark,
)
from api.contexts.community.posts import create_post, list_posts, public_post
from api.contexts.community.reactions import remove_reaction, set_reaction
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
from api.contexts.community.reports import (
    create_report,
    list_my_reports,
    list_reports,
)
from api.contexts.community.timeline import list_activities
from api.contexts.presentation.fragments import fetch
from api.db import SessionDep
from api.shared.cursor import decode, encode
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


@router.get("/me/reports/")
async def my_reports(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_my_reports(session, user_id=user.id, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/moderation/reports/")
async def moderation_reports(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(staff_user)],
    status: str = "",
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_reports(
        session, user_id=None, status=status, page=page, page_size=page_size
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.post("/reports/")
async def report(
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data = await create_report(session, reporter_id=user.id, body=body)
    except FileNotFoundError as error:
        raise ProblemError(
            status_code=404,
            detail="Community target not found.",
            code="community.target_not_found",
        ) from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201)


@router.get("/me/bookmarks/")
async def bookmarks(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
    target_type: str = "",
    keyword: str = "",
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_bookmarks(
        session,
        user_id=user.id,
        target_type=target_type,
        keyword=keyword.strip(),
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.put("/me/bookmarks/{target_type}/{target_id}/")
async def bookmark(
    target_type: str,
    target_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data, created = await set_bookmark(
            session, user_id=user.id, target_type=target_type, target_id=target_id
        )
    except KeyError as error:
        raise ProblemError(status_code=404, detail="Not found.") from error
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Community target not found.",
            code="community.target_not_found",
        ) from error
    return JSONResponse(data, status_code=201 if created else 200)


@router.delete("/me/bookmarks/{target_type}/{target_id}/", status_code=204)
async def unbookmark(
    target_type: str,
    target_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> None:
    try:
        await remove_bookmark(
            session, user_id=user.id, target_type=target_type, target_id=target_id
        )
    except (KeyError, LookupError) as error:
        raise ProblemError(status_code=404, detail="Bookmark not found.") from error


@router.put("/me/reactions/{target_type}/{target_id}/{reaction_type}/")
async def react(
    target_type: str,
    target_id: int,
    reaction_type: str,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data, created = await set_reaction(
            session,
            user_id=user.id,
            target_type=target_type,
            target_id=target_id,
            reaction_type=reaction_type,
        )
    except FileNotFoundError as error:
        raise ProblemError(
            status_code=404,
            detail="Community target not found.",
            code="community.target_not_found",
        ) from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201 if created else 200)


@router.delete("/me/reactions/{target_type}/{target_id}/{reaction_type}/", status_code=204)
async def unreact(
    target_type: str,
    target_id: int,
    reaction_type: str,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> None:
    await remove_reaction(
        session,
        user_id=user.id,
        target_type=target_type,
        target_id=target_id,
        reaction_type=reaction_type,
    )


@router.get("/me/activities/")
async def my_activities(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
    cursor: str = "",
    page_size: int = 16,
) -> dict[str, Any]:
    parsed = decode(cursor or None)
    size = min(max(page_size, 1), 64)
    results, next_cursor = await list_activities(
        session,
        viewer_id=user.id,
        owner_id=user.id,
        cursor=parsed,
        page_size=size,
    )
    return {
        "next": (
            str(request.url.include_query_params(cursor=encode(next_cursor)))
            if next_cursor is not None
            else None
        ),
        "previous": None,
        "results": results,
    }


@router.get("/activities/")
async def public_activities(
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
    cursor: str = "",
    page_size: int = 16,
) -> dict[str, Any]:
    parsed = decode(cursor or None)
    size = min(max(page_size, 1), 64)
    results, next_cursor = await list_activities(
        session,
        viewer_id=viewer.id if viewer else 0,
        owner_id=None,
        cursor=parsed,
        page_size=size,
        public_only=True,
    )
    return {
        "next": (
            str(request.url.include_query_params(cursor=encode(next_cursor)))
            if next_cursor is not None
            else None
        ),
        "previous": None,
        "results": results,
    }


@router.get("/users/{user_id}/activities/")
async def user_activities(
    user_id: int,
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
    cursor: str = "",
    page_size: int = 16,
) -> dict[str, Any]:
    parsed = decode(cursor or None)
    size = min(max(page_size, 1), 64)
    results, next_cursor = await list_activities(
        session,
        viewer_id=viewer.id if viewer else 0,
        owner_id=user_id,
        cursor=parsed,
        page_size=size,
        public_only=True,
    )
    return {
        "next": (
            str(request.url.include_query_params(cursor=encode(next_cursor)))
            if next_cursor is not None
            else None
        ),
        "previous": None,
        "results": results,
    }


@router.get("/me/feed/")
async def feed(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
    cursor: str = "",
    page_size: int = 16,
    include_self: str = "",
) -> dict[str, Any]:
    parsed = decode(cursor or None)
    size = min(max(page_size, 1), 64)
    results, next_cursor = await list_activities(
        session,
        viewer_id=user.id,
        owner_id=None,
        cursor=parsed,
        page_size=size,
        public_only=True,
        feed=True,
        include_self=include_self.lower() in {"1", "true", "yes"},
    )
    return {
        "next": (
            str(request.url.include_query_params(cursor=encode(next_cursor)))
            if next_cursor is not None
            else None
        ),
        "previous": None,
        "results": results,
    }


@router.get("/posts/")
async def posts(
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
    entity_id: str = "",
    keyword: str = "",
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_posts(
        session,
        viewer_id=viewer.id if viewer else 0,
        entity_id=entity_id,
        keyword=keyword.strip(),
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.post("/posts/")
async def add_post(
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data = await create_post(session, user_id=user.id, body=body)
    except FileNotFoundError as error:
        raise ProblemError(status_code=404, detail="Entity not found.") from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201)


@router.get("/posts/{post_id}/")
async def post_detail(
    post_id: int,
    session: SessionDep,
    viewer: Annotated[Any | None, Depends(optional_user)],
) -> dict[str, Any]:
    try:
        return await public_post(session, viewer_id=viewer.id if viewer else 0, post_id=post_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Post not found.") from error
