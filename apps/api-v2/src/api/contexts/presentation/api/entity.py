from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, is_active, is_public, resolve
from api.contexts.presentation.detail import entity_detail
from api.db import get_session
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/index", tags=["catalogue"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
NotFound = ProblemError(status_code=404, detail="Entity not found.")


@router.get("/entities/{entity_id}/")
async def entity(
    entity_id: str,
    session: SessionDep,
    accept_language: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    from uuid import UUID

    try:
        parsed = UUID(entity_id)
    except ValueError as error:
        raise ProblemError(status_code=404, detail="Entity not found.") from error
    root = await resolve(session, parsed)
    if root is None or not await is_active(session, root):
        raise ProblemError(status_code=404, detail="Entity not found.")
    ids = await cluster_ids(session, root)
    if not await is_public(session, ids):
        raise ProblemError(status_code=404, detail="Entity not found.")
    language = (accept_language or "").split(",", 1)[0]
    return await entity_detail(
        session,
        root=root,
        cluster_ids=[str(value) for value in ids],
        language=language,
    )
