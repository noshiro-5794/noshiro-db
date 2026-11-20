"""Releases a work appears in, with the release rendered as a summary."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import PROVENANCE, PROVENANCE_JOINS, fetch, row_provenance
from .summary import public_summary

CURRENT_LINK = """
    (
        NOT EXISTS (
            SELECT 1 FROM release_work_evidence WHERE release_work_id = link.id
        )
        OR EXISTS (
            SELECT 1 FROM release_work_evidence AS evidence
            JOIN provider_observation AS observation
              ON observation.id = evidence.observation_id
            LEFT JOIN provider_record AS record
              ON record.id = observation.provider_record_id
            LEFT JOIN provider_namespace AS namespace
              ON namespace.id = record.namespace_id
            LEFT JOIN provider AS provider ON provider.id = namespace.provider_id
            WHERE evidence.release_work_id = link.id
              AND observation.provider_record_id IS NOT NULL
              AND record.status = 'active'
              AND provider.redistribution_policy <> 'forbidden'
              AND EXISTS (
                SELECT 1 FROM provider_current_observation AS pointer
                WHERE pointer.observation_id = observation.id
                  AND pointer.provider_record_id = observation.provider_record_id
              )
        )
    )
"""

CURRENT_EVIDENCE = """
    observation.provider_record_id IS NOT NULL
    AND record.status = 'active'
    AND provider.redistribution_policy <> 'forbidden'
    AND EXISTS (
        SELECT 1 FROM provider_current_observation AS pointer
        WHERE pointer.observation_id = evidence.observation_id
          AND pointer.provider_record_id = observation.provider_record_id
    )
"""


def _date(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _evidence(session: AsyncSession, link_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not link_ids:
        return {}
    rows = await fetch(
        session,
        f"""
        SELECT evidence.release_work_id, evidence.json_pointer, {PROVENANCE}
        FROM release_work_evidence AS evidence
        {
            PROVENANCE_JOINS.format(
                record="observation.provider_record_id",
                observation="evidence.observation_id",
            )
        }
        WHERE evidence.release_work_id = ANY(CAST(:ids AS bigint[]))
          AND {CURRENT_EVIDENCE}
        ORDER BY evidence.id
        """,
        {"ids": link_ids},
    )
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.release_work_id, []).append(
            {**(row_provenance(row) or {}), "json_pointer": row.json_pointer}
        )
    return grouped


async def entity_releases(
    session: AsyncSession, *, cluster: list[str], language: str
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        f"""
        SELECT link.id, link.role, link.release_id,
               release.date_start, release.date_end, release.date_precision,
               release.date_raw, release.platform, release.region
        FROM release_work AS link
        JOIN release ON release.entity_id = link.release_id
        WHERE link.work_id = ANY(CAST(:ids AS uuid[]))
          AND {CURRENT_LINK}
        ORDER BY link.id
        """,
        {"ids": cluster},
    )
    evidence = await _evidence(session, [row.id for row in rows])
    releases: list[dict[str, Any]] = []
    for row in rows:
        release = await public_summary(session, entity_id=row.release_id, language=language)
        if release is None:
            continue
        releases.append(
            {
                "role": row.role,
                "release": release,
                "date_start": _date(row.date_start),
                "date_end": _date(row.date_end),
                "date_precision": row.date_precision,
                "date_raw": row.date_raw,
                "platform": row.platform,
                "region": row.region,
                "evidence": evidence.get(row.id, []),
            }
        )
    return releases
