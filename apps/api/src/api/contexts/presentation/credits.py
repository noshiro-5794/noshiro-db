"""Credit lines for a work, with the contributor rendered as a summary."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import PROVENANCE, PROVENANCE_JOINS, fetch, row_provenance
from .summary import public_summary

CURRENT_CREDIT = """
    (
        credit.observation_id IS NULL
        OR (
            observation.provider_record_id IS NOT NULL
            AND record.status = 'active'
            AND provider.redistribution_policy <> 'forbidden'
            AND EXISTS (
                SELECT 1 FROM provider_current_observation AS pointer
                WHERE pointer.observation_id = credit.observation_id
                  AND pointer.provider_record_id = observation.provider_record_id
            )
        )
    )
"""


async def entity_credits(
    session: AsyncSession, *, cluster: list[str], language: str
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        f"""
        SELECT credit.id, credit.role, credit.credited_as, credit.contributor_id,
               {PROVENANCE}
        FROM credit
        {
            PROVENANCE_JOINS.format(
                record="observation.provider_record_id",
                observation="credit.observation_id",
            )
        }
        WHERE credit.work_id = ANY(CAST(:ids AS uuid[]))
          AND {CURRENT_CREDIT}
        ORDER BY credit.id
        """,
        {"ids": cluster},
    )
    credits: list[dict[str, Any]] = []
    for row in rows:
        contributor = await public_summary(session, entity_id=row.contributor_id, language=language)
        if contributor is None:
            continue
        credits.append(
            {
                "role": row.role,
                "credited_as": row.credited_as,
                "contributor": contributor,
                "provenance": row_provenance(row),
            }
        )
    return credits
