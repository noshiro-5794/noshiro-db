"""Entity resolution: redirects decide which entity a request actually means."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MAX_REDIRECT_DEPTH = 32


async def resolve(session: AsyncSession, entity_id: UUID) -> UUID | None:
    """Follow active redirects and return the canonical entity, or None if absent."""
    row = (
        await session.execute(
            text(
                """
                WITH RECURSIVE chain(id, depth) AS (
                    SELECT CAST(:entity_id AS uuid), 0
                    UNION ALL
                    SELECT redirect.target_entity_id, chain.depth + 1
                    FROM entity_redirect AS redirect
                    JOIN chain ON redirect.source_entity_id = chain.id
                    WHERE redirect.is_active AND chain.depth < :max_depth
                )
                SELECT id FROM chain ORDER BY depth DESC LIMIT 1
                """
            ),
            {"entity_id": str(entity_id), "max_depth": MAX_REDIRECT_DEPTH},
        )
    ).first()
    return row[0] if row else None


async def cluster_ids(session: AsyncSession, root_id: UUID) -> set[UUID]:
    """The canonical entity plus every entity redirected into it."""
    rows = (
        await session.execute(
            text(
                """
                WITH RECURSIVE cluster(id) AS (
                    SELECT CAST(:root_id AS uuid)
                    UNION
                    SELECT redirect.source_entity_id
                    FROM entity_redirect AS redirect
                    JOIN cluster ON redirect.target_entity_id = cluster.id
                    WHERE redirect.is_active
                )
                SELECT id FROM cluster
                """
            ),
            {"root_id": str(root_id)},
        )
    ).all()
    return {row[0] for row in rows}


async def is_active(session: AsyncSession, entity_id: UUID) -> bool:
    """The resolved entity itself must be active; merged sources need not be."""
    row = (
        await session.execute(
            text("SELECT lifecycle FROM entity WHERE id = CAST(:entity_id AS uuid)"),
            {"entity_id": str(entity_id)},
        )
    ).first()
    return row is not None and row[0] == "active"


async def is_public(session: AsyncSession, ids: set[UUID]) -> bool:
    """Every entity in the cluster must be public, merged sources included."""
    row = (
        await session.execute(
            text(
                """
                SELECT count(*) FILTER (WHERE visibility <> 'public') AS offenders
                FROM entity WHERE id = ANY(CAST(:ids AS uuid[]))
                """
            ),
            {"ids": [str(value) for value in ids]},
        )
    ).first()
    if row is None:
        return False
    return bool(row[0] == 0)
