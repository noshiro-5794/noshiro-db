"""Credit lines for a work, with the contributor rendered as a summary."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch

from .provenance import PROVENANCE, PROVENANCE_JOINS, row_provenance
from .source_preference import priority, role_key
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
    provider_by_role: dict[str, str | None] = {}
    seen: set[tuple[str, str]] = set()
    for row in sorted(rows, key=lambda item: priority("credits", item.provider_slug)):
        role = role_key(row.role)
        if role in provider_by_role and provider_by_role[role] != row.provider_slug:
            continue
        contributor = await public_summary(session, entity_id=row.contributor_id, language=language)
        if contributor is None:
            continue
        provider_by_role[role] = row.provider_slug
        key = (role, contributor["id"])
        if key in seen:
            continue
        seen.add(key)
        credits.append(
            {
                "role": row.role,
                "credited_as": row.credited_as,
                "contributor": contributor,
                "provenance": row_provenance(row),
            }
        )
    return credits
