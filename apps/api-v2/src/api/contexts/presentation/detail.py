"""From an entity to one page: names, descriptions, facts, links, ratings, sources.

The shape of the document is the Django serializer's; the rules come from
`fragments` and the summary from `summary`, so this module only says which lists
exist and what each row carries.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import (
    PROVENANCE,
    PROVENANCE_JOINS,
    current_rows,
    fetch,
    isoformat,
    row_provenance,
    visible,
)
from .summary import entity_summary


async def _names(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="entity_name",
            alias="name",
            columns="name.text, name.language, name.script, name.region,"
            " name.kind, name.is_official, name.is_original,"
            " name.is_machine_generated, name.is_reviewed",
            record="name.provider_record_id",
        )
        + " ORDER BY name.id",
        {"ids": cluster_ids},
    )
    return [
        {
            "text": row.text,
            "language": row.language,
            "script": row.script,
            "region": row.region,
            "kind": row.kind,
            "is_official": row.is_official,
            "is_original": row.is_original,
            "is_machine_generated": row.is_machine_generated,
            "is_reviewed": row.is_reviewed,
            "provenance": row_provenance(row),
        }
        for row in rows
    ]


async def _descriptions(
    session: AsyncSession, cluster_ids: list[str], *, content_allowed: bool
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="entity_description",
            alias="description",
            columns="description.text, description.language,"
            " description.is_official, description.is_machine_generated,"
            " description.is_reviewed, description.spoiler_level,"
            " description.safety",
            record="description.provider_record_id",
        )
        + " ORDER BY description.id",
        {"ids": cluster_ids},
    )
    return [
        {
            "text": row.text,
            "language": row.language,
            "is_official": row.is_official,
            "is_machine_generated": row.is_machine_generated,
            "is_reviewed": row.is_reviewed,
            "spoiler_level": row.spoiler_level,
            "safety": row.safety,
            "provenance": row_provenance(row),
        }
        for row in rows
        if visible(row, content_allowed=content_allowed)
    ]


async def _external_links(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="external_link",
            alias="link",
            columns="link.url, link.label, link.link_type",
            record="link.provider_record_id",
        )
        + " ORDER BY link.provider_record_id, link.url, link.id",
        {"ids": cluster_ids},
    )
    return [
        {
            "url": row.url,
            "label": row.label,
            "link_type": row.link_type,
            "provenance": row_provenance(row),
        }
        for row in rows
    ]


async def _content_ratings(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="content_rating",
            alias="rating",
            columns="rating.system, rating.value, rating.region, rating.minimum_age",
            record="rating.provider_record_id",
        )
        + " ORDER BY rating.system, rating.region, rating.value, rating.id",
        {"ids": cluster_ids},
    )
    return [
        {
            "system": row.system,
            "value": row.value,
            "region": row.region,
            "minimum_age": row.minimum_age,
            "provenance": row_provenance(row),
        }
        for row in rows
    ]


async def _facts(
    session: AsyncSession,
    *,
    root: UUID,
    cluster_ids: list[str],
    content_allowed: bool,
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        """
        SELECT fact.id, fact.predicate_id, fact.value, fact.language, fact.status,
               fact.confidence, fact.spoiler_level, fact.safety,
               fact.is_machine_generated, predicate.slug AS predicate
        FROM fact
        JOIN predicate ON predicate.id = fact.predicate_id
        WHERE fact.entity_id = ANY(CAST(:ids AS uuid[]))
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
        ORDER BY predicate.slug, fact.language, fact.id
        """,
        {"ids": cluster_ids},
    )
    decisions = {
        (row.predicate_id, row.language): row.selected_fact_id
        for row in await fetch(
            session,
            "SELECT predicate_id, language, selected_fact_id"
            " FROM resolution_decision WHERE entity_id = :root AND is_active",
            {"root": str(root)},
        )
    }
    kept = [
        row
        for row in rows
        if decisions.get((row.predicate_id, row.language), row.id) in (None, row.id)
    ]
    evidence = await _evidence(session, [row.id for row in kept])
    return [
        {
            "predicate": row.predicate,
            "value": row.value,
            "language": row.language,
            "status": row.status,
            "confidence": str(row.confidence),
            "spoiler_level": row.spoiler_level,
            "safety": row.safety,
            "is_machine_generated": row.is_machine_generated,
            "evidence": evidence.get(row.id, []),
        }
        for row in kept
        if visible(row, content_allowed=content_allowed)
    ]


async def _evidence(
    session: AsyncSession, fact_ids: list[UUID]
) -> dict[UUID, list[dict[str, Any]]]:
    if not fact_ids:
        return {}
    rows = await fetch(
        session,
        f"""
        SELECT evidence.fact_id, evidence.json_pointer, {PROVENANCE}
        FROM fact_evidence AS evidence
        {
            PROVENANCE_JOINS.format(
                record="observation.provider_record_id",
                observation="evidence.observation_id",
            )
        }
        WHERE evidence.fact_id = ANY(CAST(:ids AS uuid[]))
        ORDER BY evidence.id
        """,
        {"ids": [str(value) for value in fact_ids]},
    )
    grouped: dict[UUID, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.fact_id, []).append(
            {**(row_provenance(row) or {}), "json_pointer": row.json_pointer}
        )
    return grouped


async def _sources(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        """
        SELECT representation.mapping_kind, representation.method,
               representation.confidence, record.last_seen_at,
               provider.slug AS provider_slug,
               namespace.slug AS namespace_slug,
               record.external_id AS external_id,
               record.canonical_url AS canonical_url
        FROM entity_representation AS representation
        JOIN provider_record AS record ON record.id = representation.provider_record_id
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN provider ON provider.id = namespace.provider_id
        WHERE representation.entity_id = ANY(CAST(:ids AS uuid[]))
          AND representation.is_active
          AND provider.redistribution_policy <> 'forbidden'
        ORDER BY provider.slug, namespace.slug, record.external_id
        """,
        {"ids": cluster_ids},
    )
    return [
        {
            "provider": row.provider_slug,
            "namespace": row.namespace_slug,
            "external_id": row.external_id,
            "url": row.canonical_url,
            "mapping_kind": row.mapping_kind,
            "method": row.method,
            "confidence": str(row.confidence),
            "last_seen_at": isoformat(row.last_seen_at),
        }
        for row in rows
    ]


async def entity_detail(
    session: AsyncSession,
    *,
    root: UUID,
    cluster_ids: list[str],
    language: str,
) -> dict[str, Any]:
    summary = await entity_summary(session, root=root, cluster_ids=cluster_ids, language=language)
    content_allowed = summary["audience"] != "adult"
    return {
        **summary,
        "names": await _names(session, cluster_ids),
        "descriptions": await _descriptions(session, cluster_ids, content_allowed=content_allowed),
        "facts": await _facts(
            session, root=root, cluster_ids=cluster_ids, content_allowed=content_allowed
        ),
        "external_links": await _external_links(session, cluster_ids),
        "content_ratings": await _content_ratings(session, cluster_ids),
        "sources": await _sources(session, cluster_ids),
    }
