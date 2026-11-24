"""Provider-scoped episode collections and their public read model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import PublicCluster, public_clusters
from api.db import fetch
from api.shared.pagination import page_offset

from .provenance import PROVENANCE, current_rows, row_provenance, visible
from .source_preference import priority
from .summary import choose_name

EPISODE_FIELDS = (
    "disc",
    "episode-number",
    "episode-type",
    "sort",
    "duration-seconds",
    "raw-duration",
    "air-date",
)


@dataclass(frozen=True, slots=True)
class EpisodeSource:
    entity_id: UUID
    coverage: int
    provenance: dict[str, Any]


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


async def episode_ids(
    session: AsyncSession, cluster: list[str], *, public_only: bool = True
) -> list[UUID]:
    visibility = "AND target.visibility = 'public'" if public_only else ""
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
          {visibility}
          AND {CURRENT_RELATION}
        """,
        {"ids": cluster},
    )
    return [row.id for row in rows]


async def _episode_fields(
    session: AsyncSession, ids: list[UUID], provider: str | None
) -> dict[tuple[UUID, str], Any]:
    if not ids:
        return {}
    rows = await fetch(
        session,
        """
        SELECT DISTINCT ON (fact.entity_id, predicate.slug)
               fact.entity_id, predicate.slug, fact.value
        FROM fact
        JOIN predicate ON predicate.id = fact.predicate_id
        WHERE fact.entity_id = ANY(CAST(:ids AS uuid[]))
          AND predicate.slug = ANY(CAST(:slugs AS text[]))
          AND fact.status <> 'rejected'
          AND fact.safety NOT IN ('explicit', 'suggestive') AND fact.spoiler_level = 0
          AND (
            (CAST(:provider AS text) IS NULL AND NOT EXISTS (
                SELECT 1 FROM fact_evidence WHERE fact_id = fact.id
            ))
            OR EXISTS (
              SELECT 1 FROM fact_evidence AS evidence
              JOIN provider_observation AS observation ON observation.id = evidence.observation_id
              JOIN provider_record AS record ON record.id = observation.provider_record_id
              JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
              JOIN provider AS source ON source.id = namespace.provider_id
              JOIN provider_current_observation AS pointer
                ON pointer.observation_id = observation.id
                AND pointer.provider_record_id = record.id
              WHERE evidence.fact_id = fact.id AND record.status = 'active'
                AND source.redistribution_policy <> 'forbidden'
                AND (CAST(:provider AS text) IS NULL OR source.slug = :provider)
            )
          )
        ORDER BY fact.entity_id, predicate.slug, fact.confidence DESC, fact.created_at DESC, fact.id
        """,
        {"ids": ids, "slugs": list(EPISODE_FIELDS), "provider": provider},
    )
    return {(row.entity_id, row.slug): row.value for row in rows}


def _order(episode_id: UUID, facts: dict[tuple[UUID, str], Any]) -> tuple[float, float, float, str]:
    def number(slug: str) -> float:
        try:
            return float(facts.get((episode_id, slug)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return float("inf")

    return (number("disc"), number("sort"), number("episode-number"), str(episode_id))


async def _sources(
    session: AsyncSession, ids: list[UUID], cluster: list[str]
) -> list[EpisodeSource]:
    if not ids:
        return []
    rows = await fetch(
        session,
        f"""
        WITH assignments AS (
            SELECT relation.to_entity_id AS episode_id,
                   namespace.provider_id,
                   CASE collection.normalized_data ->> 'complete'
                       WHEN 'true' THEN 0 WHEN 'false' THEN 2 ELSE 1
                   END AS coverage
            FROM entity_relation AS relation
            JOIN entity_relation_evidence AS evidence ON evidence.relation_id = relation.id
            JOIN provider_observation AS collection ON collection.id = evidence.observation_id
            JOIN provider_record AS record ON record.id = collection.provider_record_id
            JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
            JOIN provider_current_observation AS pointer
              ON pointer.observation_id = collection.id AND pointer.provider_record_id = record.id
            WHERE relation.from_entity_id = ANY(CAST(:cluster AS uuid[]))
              AND relation.relation_type = 'has-episode' AND record.status = 'active'
            UNION ALL
            SELECT relation.to_entity_id, NULL, 1
            FROM entity_relation AS relation
            WHERE relation.from_entity_id = ANY(CAST(:cluster AS uuid[]))
              AND relation.relation_type = 'has-episode'
              AND NOT EXISTS (
                  SELECT 1 FROM entity_relation_evidence WHERE relation_id = relation.id
              )
        )
        SELECT representation.entity_id, assignments.coverage, {PROVENANCE}
        FROM entity_representation AS representation
        JOIN provider_record AS record ON record.id = representation.provider_record_id
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN provider AS provider ON provider.id = namespace.provider_id
        JOIN assignments ON assignments.episode_id = representation.entity_id
          AND (assignments.provider_id IS NULL OR assignments.provider_id = provider.id)
        JOIN provider_current_observation AS pointer
          ON pointer.provider_record_id = record.id AND pointer.schema_name = 'index.episode'
        JOIN provider_observation AS observation ON observation.id = pointer.observation_id
        LEFT JOIN mapping_run AS run ON run.id = observation.mapping_run_id
        WHERE representation.entity_id = ANY(CAST(:ids AS uuid[]))
          AND representation.is_active AND record.status = 'active'
          AND provider.redistribution_policy <> 'forbidden'
        ORDER BY assignments.coverage, pointer.updated_at DESC, record.external_id, pointer.id
        """,
        {"ids": ids, "cluster": cluster},
    )
    return [
        EpisodeSource(row.entity_id, row.coverage, provenance)
        for row in rows
        if (provenance := row_provenance(row)) is not None
    ]


async def _episode_text(
    session: AsyncSession,
    members: list[str],
    language: str,
    provider: str | None,
    *,
    content_allowed: bool,
) -> tuple[str, str, str]:
    params = {"ids": members, "provider": provider}
    scope = " AND (CAST(:provider AS text) IS NULL OR provider.slug = :provider)"
    names = await fetch(
        session,
        current_rows(
            table="entity_name",
            alias="name",
            columns="name.id, name.text, name.language, name.kind,"
            " name.is_official, name.is_original",
            record="name.provider_record_id",
        )
        + scope,
        params,
    )
    descriptions = (
        await fetch(
            session,
            current_rows(
                table="entity_description",
                alias="description",
                columns="description.text, description.safety, description.spoiler_level",
                record="description.provider_record_id",
            )
            + scope
            + " ORDER BY description.id",
            params,
        )
        if content_allowed
        else []
    )
    description = next((row.text for row in descriptions if visible(row, content_allowed=True)), "")
    return choose_name(names, language), choose_name(names, "zh-Hans"), description


async def episode_page(
    session: AsyncSession,
    *,
    cluster: list[str],
    language: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    eligible = await public_clusters(session, await episode_ids(session, cluster))
    sources = await _sources(session, list(eligible), cluster)
    preferred = min(
        sources,
        key=lambda source: (source.coverage, priority("episodes", source.provenance["provider"])),
        default=None,
    )
    provider = preferred.provenance["provider"] if preferred else None
    by_root: dict[UUID, tuple[PublicCluster, dict[str, Any] | None]] = {}
    if provider is None:
        legacy = await fetch(
            session,
            """
            SELECT legacy.id FROM unnest(CAST(:ids AS uuid[])) AS legacy(id)
            WHERE NOT EXISTS (
                SELECT 1 FROM entity_representation
                WHERE entity_id = legacy.id AND is_active
            )
            """,
            {"ids": list(eligible)},
        )
        for row in legacy:
            resolved = eligible[row.id]
            by_root[resolved.root] = resolved, None
    else:
        for source in sources:
            if source.provenance["provider"] == provider:
                resolved = eligible[source.entity_id]
                by_root.setdefault(resolved.root, (resolved, source.provenance))
    all_members = sorted({member for episode, _ in by_root.values() for member in episode.members})
    fields = await _episode_fields(session, all_members, provider)
    by_episode = {
        (root, slug): next(
            (
                fields[(member, slug)]
                for member in sorted(episode.members, key=lambda member: member != root)
                if (member, slug) in fields
            ),
            None,
        )
        for root, (episode, _) in by_root.items()
        for slug in EPISODE_FIELDS
    }
    ordered = sorted(by_root, key=lambda episode: _order(episode, by_episode))
    total = len(ordered)
    offset = page_offset(page, page_size, total)
    results = []
    for episode in ordered[offset : offset + page_size]:
        entity, provenance = by_root[episode]
        scope = list(map(str, entity.members))
        title, title_cn, description = await _episode_text(
            session, scope, language, provider, content_allowed=entity.content_allowed
        )
        values = (
            {slug: by_episode[(episode, slug)] for slug in EPISODE_FIELDS}
            if entity.content_allowed
            else {}
        )
        duration_seconds = values.get("duration-seconds")
        duration = (
            str(timedelta(seconds=duration_seconds))
            if isinstance(duration_seconds, int | float)
            else None
        )
        results.append(
            {
                "id": str(episode),
                "title": title,
                "title_cn": title_cn,
                "type": values.get("episode-type") or "",
                "number": values.get("episode-number"),
                "sort": values.get("sort"),
                "disc": values.get("disc"),
                "duration": duration,
                "raw_duration": values.get("raw-duration") or "",
                "air_date": values.get("air-date"),
                "description": description,
                "provenance": provenance,
            }
        )
    return total, results
