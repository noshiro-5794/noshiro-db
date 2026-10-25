"""The entity summary: the shape every list and nested target renders."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, is_public, resolve

from .fragments import current_rows, fetch, row_provenance, visible


def choose_name(names: list[Any], language: str) -> str:
    if not names:
        return "Untitled"
    wanted = language or ""
    candidates = [
        name
        for name in names
        if name.language and wanted and name.language.lower() == wanted.lower()
    ]
    if not candidates and wanted:
        primary = wanted.split("-")[0].lower()
        candidates = [name for name in names if name.language.lower().split("-")[0] == primary]
    candidates = candidates or [
        name for name in names if name.is_original or name.kind == "original"
    ]
    candidates = candidates or names
    chosen = sorted(candidates, key=lambda item: (not item.is_official, item.id))[0]
    return str(chosen.text)


async def cluster_entities(session: AsyncSession, cluster_ids: list[str]) -> list[Any]:
    return await fetch(
        session,
        "SELECT id, kind, lifecycle, audience, spoiler_level"
        " FROM entity WHERE id = ANY(CAST(:ids AS uuid[])) ORDER BY id",
        {"ids": cluster_ids},
    )


async def _media(session: AsyncSession, scope: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="entity_media",
            alias="link",
            columns="asset.url, link.purpose, asset.safety, asset.spoiler_level",
            record="asset.provider_record_id",
            current_record="observation.provider_record_id",
            extra_join="JOIN media_asset AS asset ON asset.id = link.asset_id",
        )
        + " ORDER BY link.id",
        {"ids": scope},
    )
    return [
        {
            "url": row.url,
            "purpose": row.purpose,
            "safety": row.safety,
            "provenance": row_provenance(row),
        }
        for row in rows
        if visible(row, content_allowed=True)
    ]


async def entity_summary(
    session: AsyncSession,
    *,
    root: UUID,
    cluster_ids: list[str],
    language: str,
    cluster_scope: bool = True,
) -> dict[str, Any]:
    """The summary of one entity.

    ``cluster_scope`` decides whether names, memberships and media are read from
    the whole merge cluster or from the root alone. The single-entity endpoints
    use the cluster; the catalogue list uses the root, which is what Django's
    batched `entity_summaries` does — an inconsistency between the two paths that
    parity has to reproduce before it can be removed on both sides.
    """
    members = await cluster_entities(session, cluster_ids)
    root_row = next(row for row in members if row.id == root)
    audience = "adult" if any(row.audience == "adult" for row in members) else root_row.audience
    works = await fetch(
        session,
        "SELECT entity_id, work_type FROM work"
        " WHERE entity_id = ANY(CAST(:ids AS uuid[]))"
        " AND work_type <> 'unclassified'"
        " ORDER BY created_at, entity_id LIMIT 1",
        {"ids": cluster_ids},
    )
    if not works:
        works = await fetch(
            session,
            "SELECT entity_id, work_type FROM work WHERE entity_id = :root",
            {"root": str(root)},
        )
    scope = cluster_ids if cluster_scope else [str(root)]
    memberships = await fetch(
        session,
        "SELECT collection.slug FROM curated_membership AS membership"
        " JOIN curated_collection AS collection"
        " ON collection.id = membership.collection_id"
        " WHERE membership.entity_id = ANY(CAST(:ids AS uuid[]))"
        " AND membership.listing_state = 'listed'",
        {"ids": scope},
    )
    names = await fetch(
        session,
        current_rows(
            table="entity_name",
            alias="name",
            columns="name.id, name.text, name.language, name.kind,"
            " name.is_official, name.is_original",
            record="name.provider_record_id",
        ),
        {"ids": scope},
    )
    content_allowed = audience != "adult"
    spoiler_allowed = all(row.spoiler_level <= 0 for row in members)
    media = await _media(session, cluster_ids) if content_allowed and spoiler_allowed else []
    return {
        "id": str(root),
        "entity_type": root_row.kind,
        "lifecycle": root_row.lifecycle,
        "audience": audience,
        "work_type": works[0].work_type if works else None,
        "display_name": choose_name(names, language),
        "collections": sorted({row.slug for row in memberships}),
        "media": media,
    }


async def public_summary(
    session: AsyncSession, *, entity_id: UUID, language: str
) -> dict[str, Any] | None:
    """The summary of an entity, or None when the entity is not publicly visible."""
    root = await resolve(session, entity_id)
    if root is None:
        return None
    ids = await cluster_ids(session, root)
    if not await is_public(session, ids):
        return None
    return await entity_summary(
        session,
        root=root,
        cluster_ids=[str(value) for value in ids],
        language=language,
    )


async def preferred_name(session: AsyncSession, *, entity_id: UUID, language: str) -> str:
    """The display name for one language, without building the whole summary."""
    root = await resolve(session, entity_id)
    if root is None:
        return "Untitled"
    ids = await cluster_ids(session, root)
    names = await fetch(
        session,
        current_rows(
            table="entity_name",
            alias="name",
            columns="name.id, name.text, name.language, name.kind,"
            " name.is_official, name.is_original",
            record="name.provider_record_id",
        ),
        {"ids": [str(value) for value in ids]},
    )
    return choose_name(names, language)
