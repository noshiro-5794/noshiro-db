from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header

from api.contexts.identity.resolution import cluster_ids, is_active, is_public, resolve
from api.contexts.presentation.credits import entity_credits
from api.contexts.presentation.detail import entity_detail
from api.contexts.presentation.relations import entity_relations
from api.contexts.presentation.releases import entity_releases
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/index", tags=["catalogue"])

NOT_FOUND = "Entity not found."


def _parse_entity_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as error:
        raise ProblemError(status_code=404, detail=NOT_FOUND) from error


async def _public_cluster(session: SessionDep, raw: str) -> tuple[UUID, list[str]]:
    root = await resolve(session, _parse_entity_id(raw))
    if root is None or not await is_active(session, root):
        raise ProblemError(status_code=404, detail=NOT_FOUND)
    ids = await cluster_ids(session, root)
    if not await is_public(session, ids):
        raise ProblemError(status_code=404, detail=NOT_FOUND)
    return root, [str(value) for value in ids]


@router.get("/entities/{entity_id}/")
async def entity(
    entity_id: str,
    session: SessionDep,
    accept_language: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    root, cluster = await _public_cluster(session, entity_id)
    return await entity_detail(
        session,
        root=root,
        cluster_ids=cluster,
        language=(accept_language or "").split(",", 1)[0],
    )


@router.get("/entities/{entity_id}/relations/")
async def relations(
    entity_id: str,
    session: SessionDep,
    accept_language: Annotated[str | None, Header()] = None,
) -> list[dict[str, Any]]:
    root, cluster = await _public_cluster(session, entity_id)
    return await entity_relations(
        session,
        root=root,
        cluster=cluster,
        language=(accept_language or "").split(",", 1)[0],
    )


@router.get("/entities/{entity_id}/credits/")
async def credits(
    entity_id: str,
    session: SessionDep,
    accept_language: Annotated[str | None, Header()] = None,
) -> list[dict[str, Any]]:
    _, cluster = await _public_cluster(session, entity_id)
    return await entity_credits(
        session,
        cluster=cluster,
        language=(accept_language or "").split(",", 1)[0],
    )


@router.get("/entities/{entity_id}/releases/")
async def releases(
    entity_id: str,
    session: SessionDep,
    accept_language: Annotated[str | None, Header()] = None,
) -> list[dict[str, Any]]:
    _, cluster = await _public_cluster(session, entity_id)
    return await entity_releases(
        session,
        cluster=cluster,
        language=(accept_language or "").split(",", 1)[0],
    )
