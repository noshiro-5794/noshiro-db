from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Request

from api.contexts.identity.resolution import cluster_ids, is_active, is_public, resolve
from api.contexts.presentation.catalogue import entity_page
from api.contexts.presentation.characters import character_page
from api.contexts.presentation.credits import entity_credits
from api.contexts.presentation.detail import entity_detail
from api.contexts.presentation.episodes import episode_page
from api.contexts.presentation.evidence import entity_evidence
from api.contexts.presentation.fragments import fetch
from api.contexts.presentation.relations import entity_relations
from api.contexts.presentation.releases import entity_releases
from api.db import SessionDep
from api.shared.pagination import (
    ensure_page,
    page_params,
    page_payload,
)
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


@router.get("/entities/")
async def catalogue(
    session: SessionDep,
    request: Request,
    accept_language: Annotated[str | None, Header()] = None,
    query: str = "",
    collection: str = "",
    scope: str = "index",
    subject_type: str = "",
    ordering: str = "",
    nsfw: bool = False,
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await entity_page(
        session,
        keyword=query.strip(),
        scope=scope,
        collection=collection,
        subject_type=subject_type,
        safe_only=not nsfw,
        ordering=ordering,
        language=(accept_language or "").split(",", 1)[0],
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


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


@router.get("/entities/{entity_id}/characters/")
async def characters(
    entity_id: str,
    session: SessionDep,
    request: Request,
    accept_language: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _, cluster = await _public_cluster(session, entity_id)
    page, page_size = page_params(request)
    total, results = await character_page(
        session,
        cluster=cluster,
        language=(accept_language or "").split(",", 1)[0],
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/entities/{entity_id}/episodes/")
async def episodes(
    entity_id: str,
    session: SessionDep,
    request: Request,
    accept_language: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _, cluster = await _public_cluster(session, entity_id)
    page, page_size = page_params(request, default=64)
    total, results = await episode_page(
        session,
        cluster=cluster,
        language=(accept_language or "").split(",", 1)[0],
        page=page,
        page_size=page_size,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/entities/{entity_id}/evidence/")
async def evidence(
    entity_id: str,
    session: SessionDep,
) -> list[dict[str, Any]]:
    _, cluster = await _public_cluster(session, entity_id)
    return await entity_evidence(session, cluster=cluster)


@router.get("/collections/{slug}/entities/")
async def collection_entities(
    slug: str,
    session: SessionDep,
    request: Request,
    accept_language: Annotated[str | None, Header()] = None,
    query: str = "",
    subject_type: str = "",
    ordering: str = "",
    nsfw: bool = False,
) -> dict[str, Any]:
    exists = await fetch(
        session,
        "SELECT 1 FROM curated_collection WHERE slug = :slug AND is_enabled",
        {"slug": slug},
    )
    if not exists:
        raise ProblemError(status_code=404, detail="Index collection not found.")
    page, page_size = page_params(request)
    total, results = await entity_page(
        session,
        keyword=query.strip(),
        scope="index",
        collection=slug,
        subject_type=subject_type,
        safe_only=not nsfw,
        ordering=ordering,
        language=(accept_language or "").split(",", 1)[0],
        page=page,
        page_size=page_size,
        cluster_scope=True,
    )
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)
