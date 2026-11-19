"""Own and public review resources."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from api.contexts.access.dependencies import current_user, optional_user
from api.contexts.access.profiles import ensure_public_user
from api.contexts.library.reviews import delete_review, get_review, list_reviews, update_review
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

from .schemas import ReviewListQuery, ReviewUpdate

router = APIRouter(prefix="/api/v1/users", tags=["reviews"])


@router.get("/me/reviews/")
async def my_reviews(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(current_user)],
    query: Annotated[ReviewListQuery, Query()],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_reviews(
        session,
        viewer_id=user.id,
        user_id=user.id,
        keyword=query.keyword,
        ordering=query.ordering,
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/me/reviews/{review_id}/")
async def my_review(
    review_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await get_review(session, viewer_id=user.id, review_id=review_id, own=True)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="UserReview not found.") from error


@router.patch("/me/reviews/{review_id}/")
async def patch_review(
    review_id: int,
    body: ReviewUpdate,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await update_review(
            session,
            user_id=user.id,
            review_id=review_id,
            values=body.model_dump(exclude_unset=True),
        )
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="UserReview not found.",
            code="users.review_not_found",
        ) from error


@router.delete("/me/reviews/{review_id}/", status_code=204)
async def remove_review(
    review_id: int,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> None:
    try:
        await delete_review(session, user_id=user.id, review_id=review_id)
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="UserReview not found.",
            code="users.review_not_found",
        ) from error


@router.get("/reviews/{review_id}/")
async def public_review(
    review_id: int,
    session: SessionDep,
    viewer: Annotated[Any | None, Depends(optional_user)],
) -> dict[str, Any]:
    try:
        return await get_review(session, viewer_id=viewer.id if viewer else 0, review_id=review_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="UserReview not found.") from error


@router.get("/entities/{entity_id}/reviews/")
async def entity_reviews(
    entity_id: UUID,
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
) -> dict[str, Any]:
    page, page_size = page_params(request)
    try:
        total, results = await list_reviews(
            session,
            viewer_id=viewer.id if viewer else 0,
            entity_id=entity_id,
            public_only=True,
            ordering="-updated_at",
            page=page,
            page_size=page_size,
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Entity not found.") from error
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/{user_id}/reviews/")
async def public_user_reviews(
    user_id: int,
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
    query: str = "",
) -> dict[str, Any]:
    viewer_id = viewer.id if viewer else 0
    await ensure_public_user(session, user_id=user_id, viewer_id=viewer_id)
    page, page_size = page_params(request)
    total, results = await list_reviews(
        session,
        viewer_id=viewer_id,
        user_id=user_id,
        public_only=True,
        keyword=query,
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)
