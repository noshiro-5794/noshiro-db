"""Characters appearing in a work, paginated over the appearance rows."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import PROVENANCE, PROVENANCE_JOINS, fetch, row_provenance
from .summary import public_summary

CURRENT_APPEARANCE = """
    (
        appearance.observation_id IS NULL
        OR (
            observation.provider_record_id IS NOT NULL
            AND record.status = 'active'
            AND provider.redistribution_policy <> 'forbidden'
            AND EXISTS (
                SELECT 1 FROM provider_current_observation AS pointer
                WHERE pointer.observation_id = appearance.observation_id
                  AND pointer.provider_record_id = observation.provider_record_id
            )
        )
    )
"""

FILTER = """
    appearance.work_id = ANY(CAST(:ids AS uuid[]))
    AND appearance.spoiler_level = 0
    AND character.visibility = 'public'
    AND {current}
"""


async def character_page(
    session: AsyncSession,
    *,
    cluster: list[str],
    language: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    current = CURRENT_APPEARANCE
    count_row = await fetch(
        session,
        f"""
        SELECT count(*) AS total
        FROM appearance
        JOIN entity AS character ON character.id = appearance.character_entity_id
        {
            PROVENANCE_JOINS.format(
                record="observation.provider_record_id",
                observation="appearance.observation_id",
            )
        }
        WHERE {FILTER.format(current=current)}
        """,
        {"ids": cluster},
    )
    total = int(count_row[0].total) if count_row else 0
    rows = await fetch(
        session,
        f"""
        SELECT appearance.role, appearance.spoiler_level,
               appearance.character_entity_id, {PROVENANCE}
        FROM appearance
        JOIN entity AS character ON character.id = appearance.character_entity_id
        {
            PROVENANCE_JOINS.format(
                record="observation.provider_record_id",
                observation="appearance.observation_id",
            )
        }
        WHERE {FILTER.format(current=current)}
        ORDER BY appearance.role, appearance.character_entity_id, appearance.id
        LIMIT :limit OFFSET :offset
        """,
        {"ids": cluster, "limit": page_size, "offset": (page - 1) * page_size},
    )
    results: list[dict[str, Any]] = []
    for row in rows:
        character = await public_summary(
            session, entity_id=row.character_entity_id, language=language
        )
        if character is None:
            continue
        results.append(
            {
                "role": row.role,
                "spoiler_level": row.spoiler_level,
                "character": character,
                "provenance": row_provenance(row),
            }
        )
    return total, results
