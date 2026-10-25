from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.shared.problems import ProblemError

from ..identity.resolution import cluster_ids, is_active, is_public, resolve
from .infrastructure import list_metrics

SessionDep = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api/v1/index", tags=["catalogue"])


@router.get("/entities/{entity_id}/metrics/")
async def entity_metrics(entity_id: str, session: SessionDep) -> list[dict[str, object]]:
    try:
        parsed_id = UUID(entity_id)
    except ValueError as error:
        # Django's URL converter rejects a non-uuid with 404, not 422; the body
        # for an unmatched route is HTML there, so only the status is parity.
        raise ProblemError(status_code=404, detail="Entity not found.") from error
    root = await resolve(session, parsed_id)
    if root is None or not await is_active(session, root):
        raise ProblemError(status_code=404, detail="Entity not found.")
    ids = await cluster_ids(session, root)
    if not await is_public(session, ids):
        raise ProblemError(status_code=404, detail="Entity not found.")
    return [row.as_payload() for row in await list_metrics(session, ids)]
