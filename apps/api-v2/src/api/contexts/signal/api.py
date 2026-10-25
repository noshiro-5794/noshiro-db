from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session

from ..identity.resolution import cluster_ids, is_active, is_public, resolve
from .infrastructure import list_metrics

SessionDep = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api/v1/index", tags=["catalogue"])

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found.")


@router.get("/entities/{entity_id}/metrics/")
async def entity_metrics(entity_id: UUID, session: SessionDep) -> list[dict[str, object]]:
    root = await resolve(session, entity_id)
    if root is None or not await is_active(session, root):
        raise NOT_FOUND
    ids = await cluster_ids(session, root)
    if not await is_public(session, ids):
        raise NOT_FOUND
    return [row.as_payload() for row in await list_metrics(session, ids)]
