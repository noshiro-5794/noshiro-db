"""The entity detail read model.

The rules are the Django projector's, translated to SQL: which rows count as
"current" (the observation the mapper cursor selected for its record), how the
display name is chosen, what the safe filter hides, and in which order every list
is rendered. Ordering is explicit here because Django's unordered querysets still
return rows in insertion order, and the two responses must agree.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# A row counts as current when it has no source (source-independent), or when its
# observation is the one selected for its own provider record.
CURRENT_SUPPORT = """
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

PROVENANCE_COLUMNS = """
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
    LEFT JOIN provider_record AS record ON record.id = observation.provider_record_id
    LEFT JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
    LEFT JOIN provider AS provider ON provider.id = namespace.provider_id
"""


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    text_value = value.astimezone(UTC).isoformat()
    return text_value[:-6] + "Z" if text_value.endswith("+00:00") else text_value


def _provenance(row: Any) -> dict[str, Any] | None:
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
    if not content_allowed:
        return False
    if row.safety in {"explicit", "suggestive"}:
        return False
    return bool(getattr(row, "spoiler_level", 0) <= 0)


async def _cluster(session: AsyncSession, root: UUID) -> dict[str, Any]:
    rows = (
        await session.execute(
            text(
                "SELECT id, kind, lifecycle, audience, spoiler_level"
                " FROM entity WHERE id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": [str(root)]},
        )
    ).all()
    return {"root": rows[0] if rows else None, "members": rows}


async def _summary(
    session: AsyncSession, root: UUID, cluster_ids: list[str], language: str
) -> dict[str, Any]:
    members = (
        await session.execute(
            text(
                "SELECT id, kind, lifecycle, audience, spoiler_level"
                " FROM entity WHERE id = ANY(CAST(:ids AS uuid[])) ORDER BY id"
            ),
            {"ids": cluster_ids},
        )
    ).all()
    by_id = {row.id: row for row in members}
    root_row = by_id[root]
    audience = "adult" if any(row.audience == "adult" for row in members) else root_row.audience
    work = (
        await session.execute(
            text(
                "SELECT entity_id, work_type FROM work"
                " WHERE entity_id = ANY(CAST(:ids AS uuid[]))"
                " AND work_type <> 'unclassified'"
                " ORDER BY created_at, entity_id LIMIT 1"
            ),
            {"ids": cluster_ids},
        )
    ).first()
    if work is None:
        work = (
            await session.execute(
                text("SELECT entity_id, work_type FROM work WHERE entity_id = :root"),
                {"root": str(root)},
            )
        ).first()
    memberships = (
        await session.execute(
            text(
                "SELECT collection.slug FROM curated_membership AS membership"
                " JOIN curated_collection AS collection ON collection.id = membership.collection_id"
                " WHERE membership.entity_id = ANY(CAST(:ids AS uuid[]))"
                " AND membership.listing_state = 'listed'"
            ),
            {"ids": cluster_ids},
        )
    ).all()
    names = (
        await session.execute(
            text(
                "SELECT id, text, language, kind, is_official FROM entity_name"
                " WHERE entity_id = ANY(CAST(:ids AS uuid[]))"
                " ORDER BY kind, language, text, id"
            ),
            {"ids": cluster_ids},
        )
    ).all()
    media: list[dict[str, Any]] = []
    content_allowed = audience != "adult"
    if content_allowed and all(row.spoiler_level <= 0 for row in members):
        media_rows = (
            await session.execute(
                text(
                    "SELECT link.purpose, asset.url, asset.safety, asset.spoiler_level,"
                    " asset.provider_record_id AS record_id,"
                    + PROVENANCE_COLUMNS
                    + " FROM entity_media AS link"
                    " JOIN media_asset AS asset ON asset.id = link.asset_id"
                    + PROVENANCE_JOINS.format(observation="link.observation_id")
                    + " WHERE link.entity_id = ANY(CAST(:ids AS uuid[])) AND "
                    + CURRENT_SUPPORT.format(
                        observation="link.observation_id",
                        record="asset.provider_record_id",
                    )
                    + " ORDER BY link.id"
                ),
                {"ids": cluster_ids},
            )
        ).all()
        media = [
            {
                "url": row.url,
                "purpose": row.purpose,
                "safety": row.safety,
                "provenance": _provenance(row),
            }
            for row in media_rows
            if _visible(row, content_allowed=True)
        ]
    return {
        "id": str(root),
        "entity_type": root_row.kind,
        "lifecycle": root_row.lifecycle,
        "audience": audience,
        "work_type": work.work_type if work else None,
        "display_name": _choose_name(list(names), language),
        "collections": sorted({row.slug for row in memberships}),
        "media": media,
    }


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
    return str(sorted(candidates, key=lambda item: (not item.is_official, item.id))[0].text)


async def _names(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                "SELECT name.text, name.language, name.script, name.region, name.kind,"
                " name.is_official, name.is_original, name.is_machine_generated,"
                " name.is_reviewed,"
                + PROVENANCE_COLUMNS
                + " FROM entity_name AS name"
                + PROVENANCE_JOINS.format(observation="name.observation_id")
                + " WHERE name.entity_id = ANY(CAST(:ids AS uuid[])) AND "
                + CURRENT_SUPPORT.format(
                    observation="name.observation_id", record="name.provider_record_id"
                )
                + " ORDER BY name.id"
            ),
            {"ids": cluster_ids},
        )
    ).all()
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
            "provenance": _provenance(row),
        }
        for row in rows
    ]


async def _descriptions(
    session: AsyncSession, cluster_ids: list[str], *, content_allowed: bool
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                "SELECT description.text, description.language,"
                " description.is_official, description.is_machine_generated,"
                " description.is_reviewed, description.spoiler_level,"
                " description.safety,"
                + PROVENANCE_COLUMNS
                + " FROM entity_description AS description"
                + PROVENANCE_JOINS.format(observation="description.observation_id")
                + " WHERE description.entity_id = ANY(CAST(:ids AS uuid[])) AND "
                + CURRENT_SUPPORT.format(
                    observation="description.observation_id",
                    record="description.provider_record_id",
                )
                + " ORDER BY description.id"
            ),
            {"ids": cluster_ids},
        )
    ).all()
    return [
        {
            "text": row.text,
            "language": row.language,
            "is_official": row.is_official,
            "is_machine_generated": row.is_machine_generated,
            "is_reviewed": row.is_reviewed,
            "spoiler_level": row.spoiler_level,
            "safety": row.safety,
            "provenance": _provenance(row),
        }
        for row in rows
        if _visible(row, content_allowed=content_allowed)
    ]


async def _facts(
    session: AsyncSession, root: UUID, cluster_ids: list[str], *, content_allowed: bool
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT fact.id, fact.predicate_id, fact.value, fact.language,
                       fact.status, fact.confidence, fact.spoiler_level, fact.safety,
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
                      LEFT JOIN provider AS provider
                        ON provider.id = namespace.provider_id
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
                """
            ),
            {"ids": cluster_ids},
        )
    ).all()
    decisions = {
        (row.predicate_id, row.language): row.selected_fact_id
        for row in (
            await session.execute(
                text(
                    "SELECT predicate_id, language, selected_fact_id"
                    " FROM resolution_decision WHERE entity_id = :root AND is_active"
                ),
                {"root": str(root)},
            )
        ).all()
    }
    kept = [
        row
        for row in rows
        if decisions.get((row.predicate_id, row.language), row.id) in (None, row.id)
    ]
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
            "evidence": [evidence for evidence in (await _evidence(session, row.id))],
        }
        for row in kept
        if _visible(row, content_allowed=content_allowed)
    ]


async def _evidence(session: AsyncSession, fact_id: UUID) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                "SELECT evidence.json_pointer,"
                + PROVENANCE_COLUMNS
                + " FROM fact_evidence AS evidence"
                + PROVENANCE_JOINS.format(observation="evidence.observation_id")
                + " WHERE evidence.fact_id = :fact ORDER BY evidence.id"
            ),
            {"fact": str(fact_id)},
        )
    ).all()
    return [{**(_provenance(row) or {}), "json_pointer": row.json_pointer} for row in rows]


async def _external_links(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                "SELECT link.url, link.label, link.link_type,"
                + PROVENANCE_COLUMNS
                + " FROM external_link AS link"
                + PROVENANCE_JOINS.format(observation="link.observation_id")
                + " WHERE link.entity_id = ANY(CAST(:ids AS uuid[])) AND "
                + CURRENT_SUPPORT.format(
                    observation="link.observation_id", record="link.provider_record_id"
                )
                + " ORDER BY link.provider_record_id, link.url, link.id"
            ),
            {"ids": cluster_ids},
        )
    ).all()
    return [
        {
            "url": row.url,
            "label": row.label,
            "link_type": row.link_type,
            "provenance": _provenance(row),
        }
        for row in rows
    ]


async def _content_ratings(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                "SELECT rating.system, rating.value, rating.region, rating.minimum_age,"
                + PROVENANCE_COLUMNS
                + " FROM content_rating AS rating"
                + PROVENANCE_JOINS.format(observation="rating.observation_id")
                + " WHERE rating.entity_id = ANY(CAST(:ids AS uuid[])) AND "
                + CURRENT_SUPPORT.format(
                    observation="rating.observation_id",
                    record="rating.provider_record_id",
                )
                + " ORDER BY rating.system, rating.region, rating.value, rating.id"
            ),
            {"ids": cluster_ids},
        )
    ).all()
    return [
        {
            "system": row.system,
            "value": row.value,
            "region": row.region,
            "minimum_age": row.minimum_age,
            "provenance": _provenance(row),
        }
        for row in rows
    ]


async def _sources(session: AsyncSession, cluster_ids: list[str]) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT representation.mapping_kind, representation.method,
                       representation.confidence, record.last_seen_at,
                       provider.slug AS provider_slug,
                       namespace.slug AS namespace_slug,
                       record.external_id AS external_id,
                       record.canonical_url AS canonical_url
                FROM entity_representation AS representation
                JOIN provider_record AS record
                  ON record.id = representation.provider_record_id
                JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
                JOIN provider ON provider.id = namespace.provider_id
                WHERE representation.entity_id = ANY(CAST(:ids AS uuid[]))
                  AND representation.is_active
                  AND provider.redistribution_policy <> 'forbidden'
                ORDER BY provider.slug, namespace.slug, record.external_id
                """
            ),
            {"ids": cluster_ids},
        )
    ).all()
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
    data = await _summary(session, root, cluster_ids, language)
    content_allowed = data["audience"] != "adult"
    data["names"] = await _names(session, cluster_ids)
    data["descriptions"] = await _descriptions(
        session, cluster_ids, content_allowed=content_allowed
    )
    data["facts"] = await _facts(session, root, cluster_ids, content_allowed=content_allowed)
    data["external_links"] = await _external_links(session, cluster_ids)
    data["content_ratings"] = await _content_ratings(session, cluster_ids)
    data["sources"] = await _sources(session, cluster_ids)
    return data
