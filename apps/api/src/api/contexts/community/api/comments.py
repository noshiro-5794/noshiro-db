"""Comment creation, listing, editing and moderation endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import current_user, optional_user, staff_user
from api.contexts.community.comments import (
    create_comment,
    delete_comment,
    list_comments,
    moderate_comment,
    update_comment,
)
from api.contexts.community.errors import CommentPermissionDenied, InteractionBlocked
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

from .schemas import (
    CommentCreate,
    CommentModeration,
    CommentTarget,
    CommentUpdate,
    TargetCommentCreate,
)

router = APIRouter(prefix="/api/v1/community", tags=["community"])


@router.get("/comments/")
async def comments(
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
    query: Annotated[CommentTarget, Query()],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    try:
        total, results = await list_comments(
            session,
            viewer_id=viewer.id if viewer else 0,
            target_type=query.target_type,
            target_id=query.target_id,
            page=page,
            page_size=page_size,
        )
    except FileNotFoundError as error:
        raise ProblemError(
            status_code=404, detail="Community target not found.", code="community.target_not_found"
        ) from error
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.post("/comments/")
async def add_comment(
    body: TargetCommentCreate,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data = await create_comment(
            session,
            user_id=user.id,
            target_type=body.target_type,
            target_id=body.target_id,
            body=body.model_dump(),
        )
    except InteractionBlocked as error:
        raise ProblemError(
            status_code=403,
            detail="The community interaction is blocked.",
            code="community.interaction_blocked",
        ) from error
    except PermissionError as error:
        raise ProblemError(
            status_code=409,
            detail="The community target is locked.",
            code="community.target_locked",
        ) from error
    except FileNotFoundError as error:
        raise ProblemError(
            status_code=404, detail="Community target not found.", code="community.target_not_found"
        ) from error
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Community comment not found.",
            code="community.comment_not_found",
        ) from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201)


@router.get("/posts/{post_id}/comments/")
async def post_comments(
    post_id: int,
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    try:
        total, results = await list_comments(
            session,
            viewer_id=viewer.id if viewer else 0,
            target_type="post",
            target_id=post_id,
            page=page,
            page_size=page_size,
        )
    except FileNotFoundError as error:
        raise ProblemError(
            status_code=404, detail="Community post not found.", code="community.post_not_found"
        ) from error
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.post("/posts/{post_id}/comments/")
async def add_post_comment(
    post_id: int,
    body: CommentCreate,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> JSONResponse:
    try:
        data = await create_comment(
            session, user_id=user.id, target_type="post", target_id=post_id, body=body.model_dump()
        )
    except InteractionBlocked as error:
        raise ProblemError(
            status_code=403,
            detail="The community interaction is blocked.",
            code="community.interaction_blocked",
        ) from error
    except PermissionError as error:
        raise ProblemError(
            status_code=409,
            detail="The community target is locked.",
            code="community.target_locked",
        ) from error
    except FileNotFoundError as error:
        raise ProblemError(
            status_code=404,
            detail="Community post not found.",
            code="community.post_not_found",
        ) from error
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Community comment not found.",
            code="community.comment_not_found",
        ) from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=201)


@router.patch("/comments/{comment_id}/")
async def patch_comment(
    comment_id: int,
    body: CommentUpdate,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await update_comment(
            session,
            user_id=user.id,
            comment_id=comment_id,
            body=body.model_dump(exclude_unset=True),
        )
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Community comment not found.",
            code="community.comment_not_found",
        ) from error
    except CommentPermissionDenied as error:
        raise ProblemError(
            status_code=403,
            detail="You do not have permission to perform this action.",
            code="community.permission_denied",
        ) from error
    except PermissionError as error:
        raise ProblemError(
            status_code=409,
            detail="The community target is locked.",
            code="community.target_locked",
        ) from error
    except KeyError as error:
        raise ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors={"non_field_errors": ["No fields to update."]},
        ) from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error


@router.delete("/comments/{comment_id}/", status_code=204)
async def remove_comment(
    comment_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> None:
    try:
        await delete_comment(session, user_id=user.id, comment_id=comment_id)
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Community comment not found.",
            code="community.comment_not_found",
        ) from error
    except CommentPermissionDenied as error:
        raise ProblemError(
            status_code=403,
            detail="You do not have permission to perform this action.",
            code="community.permission_denied",
        ) from error
    except PermissionError as error:
        raise ProblemError(
            status_code=409,
            detail="The community target is locked.",
            code="community.target_locked",
        ) from error


@router.patch("/moderation/comments/{comment_id}/")
async def moderate_a_comment(
    comment_id: int,
    body: CommentModeration,
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> dict[str, Any]:
    try:
        return await moderate_comment(
            session, moderator_id=user.id, comment_id=comment_id, body=body.model_dump()
        )
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Community comment not found.",
            code="community.comment_not_found",
        ) from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
