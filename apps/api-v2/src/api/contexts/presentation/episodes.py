"""Episodes of a work, ordered by disc, sort and number rather than by id.

An episode carries its position as facts, and entity ids are random UUIDs, so the
order has to be computed: read the three facts once, sort in memory, then page.
The payload mixes facts and the episode's own detail document, as Django does.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, is_active, is_public, resolve

from .detail import entity_detail
from .fragments import PROVENANCE, fetch, row_provenance
from .summary import preferred_name

ORDERING_SLUGS = ("disc", "episode-number", "sort")

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


async def _episode_ids(session: AsyncSession, cluster: list[str]) -> list[UUID]:
    rows = await fetch(
        session,
        f"""
        SELECT DISTINCT relation.to_entity_id AS id
        FROM entity_relation AS relation
        JOIN entity AS target ON target.id = relation.to_entity_id
        WHERE relation.from_entity_id = ANY(CAST(:ids AS uuid[]))
          AND relation.relation_type = 'has-episode'
          AND target.kind = 'episode'
          AND target.lifecycle = 'active'
          AND target.visibility = 'public'
          AND {CURRENT_RELATION}
        """,
        {"ids": cluster},
    )
    return [row.id for row in rows]


async def _ordering_facts(session: AsyncSession, ids: list[UUID]) -> dict[tuple[UUID, str], Any]:
    if not ids:
        return {}
    rows = await fetch(
        session,
        """
        SELECT fact.entity_id, predicate.slug, fact.value
        FROM fact
        JOIN predicate ON predicate.id = fact.predicate_id
        WHERE fact.entity_id = ANY(CAST(:ids AS uuid[]))
          AND predicate.slug = ANY(CAST(:slugs AS text[]))
          AND fact.status <> 'rejected'
          AND (
            NOT EXISTS (SELECT 1 FROM fact_evidence WHERE fact_id = fact.id)
            OR EXISTS (
              SELECT 1 FROM fact_evidence AS evidence
              JOIN provider_observation AS observation
                ON observation.id = evidence.observation_id
              LEFT JOIN provider_record AS record
                ON record.id = observation.provider_record_id
              LEFT JOIN provider_namespace AS namespace
                ON namespace.id = record.namespace_id
              LEFT JOIN provider AS provider ON provider.id = namespace.provider_id
              WHERE evidence.fact_id = fact.id
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
        """,
        {"ids": [str(value) for value in ids], "slugs": list(ORDERING_SLUGS)},
    )
    return {(row.entity_id, row.slug): row.value for row in rows}


def _order(episode_id: UUID, facts: dict[tuple[UUID, str], Any]) -> tuple[float, float, float, str]:
    def number(slug: str) -> float:
        try:
            return float(facts.get((episode_id, slug)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return float("inf")

    return (number("disc"), number("sort"), number("episode-number"), str(episode_id))


async def _provenance(session: AsyncSession, episode: UUID) -> dict[str, Any] | None:
    rows = await fetch(
        session,
        f"""
        SELECT {PROVENANCE}
        FROM entity_representation AS representation
        JOIN provider_record AS record ON record.id = representation.provider_record_id
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN provider AS provider ON provider.id = namespace.provider_id
        JOIN provider_current_observation AS pointer
          ON pointer.provider_record_id = record.id
         AND pointer.schema_name = 'index.episode'
        JOIN provider_observation AS observation ON observation.id = pointer.observation_id
        LEFT JOIN mapping_run AS run ON run.id = observation.mapping_run_id
        WHERE representation.entity_id = CAST(:episode AS uuid)
          AND representation.is_active
        ORDER BY provider.slug, record.external_id, pointer.id
        LIMIT 1
        """,
        {"episode": str(episode)},
    )
    return row_provenance(rows[0]) if rows else None


def _fact_value(facts: list[dict[str, Any]], slug: str) -> Any:
    for fact in facts:
        if fact["predicate"] == slug:
            return fact["value"]
    return None


async def episode_page(
    session: AsyncSession,
    *,
    cluster: list[str],
    language: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    ids = await _episode_ids(session, cluster)
    facts = await _ordering_facts(session, ids)
    ordered = sorted(ids, key=lambda episode: _order(episode, facts))
    total = len(ordered)
    window = ordered[(page - 1) * page_size : page * page_size]
    results: list[dict[str, Any]] = []
    for episode in window:
        root = await resolve(session, episode)
        if root is None or not await is_active(session, root):
            continue
        episode_cluster = await cluster_ids(session, root)
        if not await is_public(session, episode_cluster):
            continue
        detail = await entity_detail(
            session,
            root=root,
            cluster_ids=[str(value) for value in episode_cluster],
            language=language,
        )
        episode_facts = detail["facts"]
        duration_seconds = _fact_value(episode_facts, "duration-seconds")
        duration = (
            str(timedelta(seconds=duration_seconds))
            if isinstance(duration_seconds, int | float)
            else None
        )
        descriptions = detail["descriptions"]
        results.append(
            {
                "id": str(root),
                "title": await preferred_name(session, entity_id=root, language=language),
                "title_cn": await preferred_name(session, entity_id=root, language="zh-Hans"),
                "type": _fact_value(episode_facts, "episode-type") or "",
                "number": _fact_value(episode_facts, "episode-number"),
                "sort": _fact_value(episode_facts, "sort"),
                "disc": _fact_value(episode_facts, "disc"),
                "duration": duration,
                "raw_duration": _fact_value(episode_facts, "raw-duration") or "",
                "air_date": _fact_value(episode_facts, "air-date"),
                "comment_count": _fact_value(episode_facts, "comment-count"),
                "description": descriptions[0]["text"] if descriptions else "",
                "provenance": await _provenance(session, root),
            }
        )
    return total, results
