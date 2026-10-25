from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header

from api.contexts.identity.resolution import cluster_ids, is_active, is_public, resolve
from api.contexts.presentation.detail import entity_detail
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/index", tags=["catalogue"])

NOT_FOUND = "Entity not found."


def _parse_entity_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as error:
        raise ProblemError(status_code=404, detail=NOT_FOUND) from error


@router.get("/entities/{entity_id}/")
async def entity(
    entity_id: str,
    session: SessionDep,
    accept_language: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    root = await resolve(session, _parse_entity_id(entity_id))
    if root is None or not await is_active(session, root):
        raise ProblemError(status_code=404, detail=NOT_FOUND)
    ids = await cluster_ids(session, root)
    if not await is_public(session, ids):
        raise ProblemError(status_code=404, detail=NOT_FOUND)
    return await entity_detail(
        session,
        root=root,
        cluster_ids=[str(value) for value in ids],
        language=(accept_language or "").split(",", 1)[0],
    )
