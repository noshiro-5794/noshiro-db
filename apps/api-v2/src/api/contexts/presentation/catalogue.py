"""The catalogue list: filters, ordering and paging over canonical entities.

A row is a *canonical* entity: a membership or a keyword match that points at an
entity merged into another one is collapsed onto its target, which is what keeps
the list stable across merges.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import fetch
from .summary import entity_summary

DEFAULT_COLLECTIONS = ("anime", "galgame")
POPULAR_ORDERING = "popular"

COLLAPSE = """
    SELECT redirect.target_entity_id AS id
    FROM entity_redirect AS redirect
    WHERE redirect.is_active AND redirect.source_entity_id IN ({source})
    UNION
    SELECT seed.id FROM ({source}) AS seed
    WHERE seed.id NOT IN (
        SELECT source_entity_id FROM entity_redirect
        WHERE is_active AND source_entity_id IN ({source})
    )
"""

MEMBERS = """
    SELECT membership.entity_id AS id
    FROM curated_membership AS membership
    JOIN curated_collection AS collection
      ON collection.id = membership.collection_id
    WHERE collection.slug = ANY(CAST(:slugs AS text[]))
      AND membership.listing_state = 'listed'
"""

MATCHES = """
    SELECT name.entity_id AS id
    FROM entity_name AS name
    WHERE strpos(lower(name.text), lower(:keyword)) > 0
    UNION
    SELECT link.entity_id AS id
    FROM external_link AS link
    WHERE strpos(lower(link.url), lower(:keyword)) > 0
"""


def _clauses(
    *,
    use_collection: bool,
    use_keyword: bool,
    subject_type: str,
    safe_only: bool,
) -> list[str]:
    clauses = [
        "entity.lifecycle = 'active'",
        "entity.visibility = 'public'",
    ]
    if use_collection:
        clauses.append(f"entity.id IN ({COLLAPSE.format(source=MEMBERS)})")
    if use_keyword:
        clauses.append(f"entity.id IN ({COLLAPSE.format(source=MATCHES)})")
    if subject_type:
        clauses.append("entity.id IN (SELECT entity_id FROM work WHERE work_type = :subject_type)")
    if safe_only:
        clauses.append("entity.audience <> 'adult'")
    return clauses


def _order(ordering: str) -> str:
    if ordering == POPULAR_ORDERING:
        return "work.popularity DESC NULLS LAST, entity.updated_at DESC, entity.id"
    return "entity.updated_at DESC, entity.id"


async def entity_page(
    session: AsyncSession,
    *,
    keyword: str,
    scope: str,
    collection: str,
    subject_type: str,
    safe_only: bool,
    ordering: str,
    language: str,
    page: int,
    page_size: int,
    cluster_scope: bool = False,
) -> tuple[int, list[dict[str, Any]]]:
    use_collection = bool(collection) or scope != "all"
    use_keyword = bool(keyword)
    where = " AND ".join(
        _clauses(
            use_collection=use_collection,
            use_keyword=use_keyword,
            subject_type=subject_type,
            safe_only=safe_only,
        )
    )
    params: dict[str, Any] = {}
    if use_collection:
        params["slugs"] = [collection] if collection else list(DEFAULT_COLLECTIONS)
    if use_keyword:
        params["keyword"] = keyword
    if subject_type:
        params["subject_type"] = subject_type

    total_rows = await fetch(session, f"SELECT count(*) AS total FROM entity WHERE {where}", params)
    total = int(total_rows[0].total) if total_rows else 0
    rows = await fetch(
        session,
        f"""
        SELECT entity.id
        FROM entity
        LEFT JOIN work ON work.entity_id = entity.id
        WHERE {where}
        ORDER BY {_order(ordering)}
        LIMIT :limit OFFSET :offset
        """,
        {**params, "limit": page_size, "offset": (page - 1) * page_size},
    )
    roots = [row.id for row in rows]
    clusters = await _clusters(session, roots)
    return total, [
        await entity_summary(
            session,
            root=root,
            cluster_ids=[str(value) for value in clusters.get(root, {root})],
            language=language,
            cluster_scope=cluster_scope,
        )
        for root in roots
    ]


async def _clusters(session: AsyncSession, roots: list[UUID]) -> dict[UUID, set[UUID]]:
    if not roots:
        return {}
    rows = await fetch(
        session,
        """
        WITH RECURSIVE cluster(root, id) AS (
            SELECT seed.id, seed.id FROM unnest(CAST(:roots AS uuid[])) AS seed(id)
            UNION
            SELECT cluster.root, redirect.source_entity_id
            FROM entity_redirect AS redirect
            JOIN cluster ON redirect.target_entity_id = cluster.id
            WHERE redirect.is_active
        )
        SELECT root, id FROM cluster
        """,
        {"roots": [str(root) for root in roots]},
    )
    grouped: dict[UUID, set[UUID]] = {root: {root} for root in roots}
    for row in rows:
        grouped.setdefault(row.root, {row.root}).add(row.id)
    return grouped
