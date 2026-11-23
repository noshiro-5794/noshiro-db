"""Relations from one entity to others, with the targets rendered as summaries."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import public_clusters
from api.db import fetch

from .provenance import PROVENANCE, PROVENANCE_JOINS, row_provenance
from .source_preference import priority
from .summary import entity_summary

CURRENT_RELATION = """
    (
        NOT EXISTS (
            SELECT 1 FROM entity_relation_evidence WHERE relation_id = relation.id
        )
        OR EXISTS (
            SELECT 1 FROM entity_relation_evidence AS evidence
            JOIN provider_observation AS observation
              ON observation.id = evidence.observation_id
            LEFT JOIN provider_record AS record
              ON record.id = observation.provider_record_id
            LEFT JOIN provider_namespace AS namespace
              ON namespace.id = record.namespace_id
            LEFT JOIN provider AS provider ON provider.id = namespace.provider_id
            WHERE evidence.relation_id = relation.id
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


async def _evidence(
    session: AsyncSession, relation_ids: list[int]
) -> dict[int, list[dict[str, Any]]]:
    if not relation_ids:
        return {}
    rows = await fetch(
        session,
        f"""
        SELECT evidence.relation_id, evidence.json_pointer, {PROVENANCE}
        FROM entity_relation_evidence AS evidence
        {
            PROVENANCE_JOINS.format(
                record="observation.provider_record_id",
                observation="evidence.observation_id",
            )
        }
        WHERE evidence.relation_id = ANY(CAST(:ids AS bigint[]))
          AND observation.provider_record_id IS NOT NULL
          AND record.status = 'active'
          AND provider.redistribution_policy <> 'forbidden'
          AND EXISTS (
            SELECT 1 FROM provider_current_observation AS pointer
            WHERE pointer.observation_id = evidence.observation_id
              AND pointer.provider_record_id = observation.provider_record_id
          )
        ORDER BY evidence.id
        """,
        {"ids": relation_ids},
    )
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.relation_id, []).append(
            {**(row_provenance(row) or {}), "json_pointer": row.json_pointer}
        )
    return grouped


async def entity_relations(
    session: AsyncSession,
    *,
    root: UUID,
    cluster: list[str],
    language: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        f"""
        SELECT relation.id, relation.relation_type, relation.to_entity_id,
               relation.qualifiers
        FROM entity_relation AS relation
        WHERE relation.from_entity_id = ANY(CAST(:ids AS uuid[]))
          AND relation.relation_type <> 'has-episode'
          AND {CURRENT_RELATION}
        ORDER BY relation.id
        """,
        {"ids": cluster},
    )
    evidence = await _evidence(session, [row.id for row in rows])
    targets = await public_clusters(session, list({row.to_entity_id for row in rows}))
    for sources in evidence.values():
        sources.sort(key=lambda source: priority("relations", source["provider"]))

    def relation_priority(row: Any) -> tuple[int, str]:
        sources = evidence.get(row.id, [])
        return priority("relations", sources[0]["provider"] if sources else None)

    rendered: list[dict[str, Any]] = []
    seen: set[tuple[str, UUID]] = set()
    for row in sorted(rows, key=relation_priority):
        target = targets.get(row.to_entity_id)
        if target is None or target.root == root:
            continue
        key = (row.relation_type, target.root)
        if key in seen:
            continue
        seen.add(key)
        rendered.append(
            {
                "relation_type": row.relation_type,
                "target": await entity_summary(
                    session,
                    root=target.root,
                    cluster_ids=list(map(str, target.members)),
                    language=language,
                ),
                "qualifiers": row.qualifiers,
                "evidence": evidence.get(row.id, []),
            }
        )
        if limit is not None and len(rendered) >= limit:
            break
    return rendered
