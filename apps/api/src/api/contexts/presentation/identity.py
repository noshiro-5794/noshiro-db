"""In-memory identity resolution for pages that hold many entities.

A calendar page can reference hundreds of works. Asking the database to resolve
each one costs a query per hop, so the redirect map is read once and followed
here, exactly as the Django views do it.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import fetch


def redirect_map(rows: list[Any]) -> dict[UUID, UUID]:
    """Follow each redirect chain to its final target."""
    redirects = {row.source_entity_id: row.target_entity_id for row in rows}
    resolved: dict[UUID, UUID] = {}

    def walk(entity_id: UUID) -> UUID:
        if entity_id in resolved:
            return resolved[entity_id]
        seen: list[UUID] = []
        current = entity_id
        while current in redirects and current not in seen:
            seen.append(current)
            current = redirects[current]
        for value in seen:
            resolved[value] = current
        resolved[entity_id] = current
        return current

    for entity_id in list(redirects):
        walk(entity_id)
    return resolved


async def load_redirects(session: AsyncSession) -> dict[UUID, UUID]:
    return redirect_map(
        await fetch(
            session,
            "SELECT source_entity_id, target_entity_id FROM entity_redirect WHERE is_active",
            {},
        )
    )


def root_of(entity_id: UUID, resolved: dict[UUID, UUID]) -> UUID:
    return resolved.get(entity_id, entity_id)


def clusters(roots: set[UUID], resolved: dict[UUID, UUID]) -> dict[UUID, set[UUID]]:
    """Every redirect source that resolves to each root, plus the root itself."""
    grouped: dict[UUID, set[UUID]] = {root: {root} for root in roots}
    for source, target in resolved.items():
        if target in grouped:
            grouped[target].add(source)
    return grouped


async def load_entities(session: AsyncSession, ids: set[UUID]) -> dict[UUID, Any]:
    rows = await fetch(
        session,
        "SELECT id, lifecycle, visibility FROM entity WHERE id = ANY(CAST(:ids AS uuid[]))",
        {"ids": [str(value) for value in ids]},
    )
    return {row.id: row for row in rows}


def publicly_visible(root: UUID, grouped: dict[UUID, set[UUID]], entities: dict[UUID, Any]) -> bool:
    members = grouped.get(root, {root})
    return bool(members) and all(
        entities.get(member) is not None and entities[member].visibility == "public"
        for member in members
    )
