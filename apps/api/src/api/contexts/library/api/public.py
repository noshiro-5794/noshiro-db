"""Another account's shared library and collections."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from api.contexts.access.dependencies import optional_user
from api.contexts.access.profiles import ensure_public_user
from api.contexts.library.collections import list_items, list_public_collections, public_collection
from api.contexts.library.entries import list_entries
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

from .schemas import PublicLibraryQuery

router = APIRouter(prefix="/api/v1/users", tags=["library"])


@router.get("/{user_id}/collections/")
async def public_collections(
    user_id: int,
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
    keyword: str = "",
    ordering: str = "id",
) -> dict[str, Any]:
    await ensure_public_user(session, user_id=user_id, viewer_id=viewer.id if viewer else 0)
    page, page_size = page_params(request)
    total, results = await list_public_collections(
        session,
        viewer_id=viewer.id if viewer else 0,
        user_id=user_id,
        keyword=keyword.strip(),
        ordering=ordering,
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/{user_id}/collections/{collection_id}/")
async def collection(
    user_id: int,
    collection_id: int,
    session: SessionDep,
    viewer: Annotated[Any | None, Depends(optional_user)],
) -> dict[str, Any]:
    viewer_id = viewer.id if viewer else 0
    await ensure_public_user(session, user_id=user_id, viewer_id=viewer_id)
    try:
        return await public_collection(
            session, viewer_id=viewer_id, user_id=user_id, collection_id=collection_id
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="UserCollection not found.") from error


@router.get("/{user_id}/collections/{collection_id}/items/")
async def collection_items(
    user_id: int,
    collection_id: int,
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
) -> dict[str, Any]:
    viewer_id = viewer.id if viewer else 0
    await ensure_public_user(session, user_id=user_id, viewer_id=viewer_id)
    page, page_size = page_params(request)
    try:
        total, results = await list_items(
            session,
            viewer_id=viewer_id,
            user_id=user_id,
            collection_id=collection_id,
            page=page,
            page_size=page_size,
            public_only=True,
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="UserCollection not found.") from error
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/{user_id}/library/entries/")
async def public_library(
    user_id: int,
    session: SessionDep,
    request: Request,
    viewer: Annotated[Any | None, Depends(optional_user)],
    query: Annotated[PublicLibraryQuery, Query()],
) -> dict[str, Any]:
    await ensure_public_user(session, user_id=user_id, viewer_id=viewer.id if viewer else 0)
    page, page_size = page_params(request)
    total, results = await list_entries(
        session,
        user_id=user_id,
        status=query.status or "",
        subject_type=query.subject_type or "",
        keyword=query.keyword,
        ordering=query.ordering,
        tag_id=0,
        page=page,
        page_size=page_size,
        public_only=True,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)
