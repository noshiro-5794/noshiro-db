"""The entity detail read model.

Every list is built the same way, so the rules are stated once instead of eleven
times:

``provenance``  the row's own ``provider_record`` plus its ``observation``;
``current``     source-independent, or supported by the observation the mapper
                cursor selected for that same record;
``safe``        the public projection hides adult and spoiler content;
``order``       explicit, because Django's unordered querysets still return rows
                in insertion order and both responses must agree.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PROVENANCE = """
    provider.slug AS provider_slug,
    namespace.slug AS namespace_slug,
    record.external_id AS external_id,
    observation.id AS observation_id,
    run.revision_id AS revision_id,
    observation.observed_at AS observed_at
"""

PROVENANCE_JOINS = """
    LEFT JOIN provider_observation AS observation ON observation.id = {observation}
    LEFT JOIN mapping_run AS run ON run.id = observation.mapping_run_id
    LEFT JOIN provider_record AS record ON record.id = {record}
    LEFT JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
    LEFT JOIN provider AS provider ON provider.id = namespace.provider_id
"""

CURRENT = """
    (
        ({observation} IS NULL AND {record} IS NULL)
        OR (
            {observation} IS NOT NULL
            AND observation.provider_record_id IS NOT NULL
            AND record.status = 'active'
            AND provider.redistribution_policy <> 'forbidden'
            AND EXISTS (
                SELECT 1 FROM provider_current_observation AS pointer
                WHERE pointer.observation_id = {observation}
                  AND pointer.provider_record_id = observation.provider_record_id
            )
        )
    )
"""


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    rendered = value.astimezone(UTC).isoformat()
    return rendered[:-6] + "Z" if rendered.endswith("+00:00") else rendered


def _row_provenance(row: Any) -> dict[str, Any] | None:
    if row.provider_slug is None:
        return None
    return {
        "provider": row.provider_slug,
        "namespace": row.namespace_slug,
        "external_id": row.external_id,
        "observation_id": str(row.observation_id) if row.observation_id else None,
        "revision_id": str(row.revision_id) if row.revision_id else None,
        "observed_at": _isoformat(row.observed_at),
    }


def _visible(row: Any, *, content_allowed: bool) -> bool:
    if not content_allowed or row.safety in {"explicit", "suggestive"}:
        return False
    return bool(getattr(row, "spoiler_level", 0) <= 0)


async def _fetch(session: AsyncSession, sql: str, params: dict[str, Any]) -> list[Any]:
    return list((await session.execute(text(sql), params)).all())


def _current_rows(
    *,
    table: str,
    alias: str,
    columns: str,
    record: str,
    extra_join: str = "",
) -> str:
    """A current-row query for a table that carries its own provenance columns."""
    observation = f"{alias}.observation_id"
    return f"""
        SELECT {columns}, {PROVENANCE}
        FROM {table} AS {alias}
        {extra_join}
        {PROVENANCE_JOINS.format(record=record, observation=observation)}
        WHERE {alias}.entity_id = ANY(CAST(:ids AS uuid[]))
          AND {CURRENT.format(record=record, observation=observation)}
    """


def _choose_name(names: list[Any], language: str) -> str:
    if not names:
        return "Untitled"
    wanted = language or ""
    candidates = [
        name
        for name in names
        if name.language and wanted and name.language.lower() == wanted.lower()
    ]
    if not candidates and wanted:
        primary = wanted.split("-")[0].lower()
        candidates = [name for name in names if name.language.lower().split("-")[0] == primary]
    candidates = candidates or [name for name in names if name.kind == "original"]
    candidates = candidates or names
    chosen = sorted(candidates, key=lambda item: (not item.is_official, item.id))[0]
    return str(chosen.text)


async def _cluster_entities(session: AsyncSession, cluster_ids: list[str]) -> list[Any]:
    return await _fetch(
        session,
        "SELECT id, kind, lifecycle, audience, spoiler_level"
        " FROM entity WHERE id = ANY(CAST(:ids AS uuid[])) ORDER BY id",
        {"ids": cluster_ids},
    )


async def _summary(
    session: AsyncSession,
    *,
    root: UUID,
    cluster_ids: list[str],
    language: str,
) -> dict[str, Any]:
    members = await _cluster_entities(session, cluster_ids)
    root_row = next(row for row in members if row.id == root)
    audience = "adult" if any(row.audience == "adult" for row in members) else root_row.audience
    works = await _fetch(
        session,
        "SELECT entity_id, work_type FROM work"
        " WHERE entity_id = ANY(CAST(:ids AS uuid[]))"
        " AND work_type <> 'unclassified'"
        " ORDER BY created_at, entity_id LIMIT 1",
        {"ids": cluster_ids},
    )
    if not works:
        works = await _fetch(
            session,
            "SELECT entity_id, work_type FROM work WHERE entity_id = :root",
            {"root": str(root)},
        )
    memberships = await _fetch(
        session,
        "SELECT collection.slug FROM curated_membership AS membership"
        " JOIN curated_collection AS collection"
        " ON collection.id = membership.collection_id"
        " WHERE membership.entity_id = ANY(CAST(:ids AS uuid[]))"
        " AND membership.listing_state = 'listed'",
        {"ids": cluster_ids},
    )
    names = await _fetch(
        session,
        "SELECT id, text, language, kind, is_official FROM entity_name"
        " WHERE entity_id = ANY(CAST(:ids AS uuid[]))"
        " ORDER BY kind, language, text, id",
        {"ids": cluster_ids},
    )
    content_allowed = audience != "adult"
    spoiler_allowed = all(row.spoiler_level <= 0 for row in members)
    media = await _media(session, cluster_ids) if content_allowed and spoiler_allowed else []
    return {
        "id": str(root),
        "entity_type": root_row.kind,
        "lifecycle": root_row.lifecycle,
        "audience": audience,
        "work_type": works[0].work_type if works else None,
        "display_name": _choose_name(names, language),
        "collections": sorted({row.slug for row in memberships}),
        "media": media,
    }


async def _media(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await _fetch(
        session,
        _current_rows(
            table="entity_media",
            alias="link",
            columns="asset.url, link.purpose, asset.safety, asset.spoiler_level",
            record="asset.provider_record_id",
            extra_join="JOIN media_asset AS asset ON asset.id = link.asset_id",
        )
        + " ORDER BY link.id",
        {"ids": cluster_ids},
    )
    return [
        {
            "url": row.url,
            "purpose": row.purpose,
            "safety": row.safety,
            "provenance": _row_provenance(row),
        }
        for row in rows
        if _visible(row, content_allowed=True)
    ]


async def _names(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await _fetch(
        session,
        _current_rows(
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
            "provenance": _row_provenance(row),
        }
        for row in rows
    ]


async def _descriptions(
    session: AsyncSession, cluster_ids: list[str], *, content_allowed: bool
) -> list[dict[str, Any]]:
    rows = await _fetch(
        session,
        _current_rows(
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
            "provenance": _row_provenance(row),
        }
        for row in rows
        if _visible(row, content_allowed=content_allowed)
    ]


async def _external_links(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await _fetch(
        session,
        _current_rows(
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
            "provenance": _row_provenance(row),
        }
        for row in rows
    ]


async def _content_ratings(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await _fetch(
        session,
        _current_rows(
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
            "provenance": _row_provenance(row),
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
    rows = await _fetch(
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
        for row in await _fetch(
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
        if _visible(row, content_allowed=content_allowed)
    ]


async def _evidence(
    session: AsyncSession, fact_ids: list[UUID]
) -> dict[UUID, list[dict[str, Any]]]:
    if not fact_ids:
        return {}
    rows = await _fetch(
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
            {**(_row_provenance(row) or {}), "json_pointer": row.json_pointer}
        )
    return grouped


async def _sources(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = await _fetch(
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
            "last_seen_at": _isoformat(row.last_seen_at),
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
    summary = await _summary(session, root=root, cluster_ids=cluster_ids, language=language)
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
