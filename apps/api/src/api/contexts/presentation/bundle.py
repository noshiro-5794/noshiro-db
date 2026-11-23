"""The bundle a display generator receives.

Smaller than the detail document on purpose: only what a page renders, each item
carrying the id it must cite back, and internal signals left out entirely. Fixed
ordering and a content hash make a rerun with the same input a no-op instead of a
new draft.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch

from .provenance import current_rows
from .summary import entity_summary

BUNDLE_VERSION = "v2"

MAX_NAMES = 20
MAX_DESCRIPTIONS = 3
MAX_MEDIA = 6
MAX_ALTERNATES = 2
DESCRIPTION_CHARS = 1500
AI_SOURCE = " AND (NOT :for_ai OR provider.ai_usage_policy = 'allowed')"
FACT_POLICY = """
    AND fact.safety NOT IN ('explicit', 'suggestive') AND fact.spoiler_level = 0
    AND (
        (NOT :for_ai AND NOT EXISTS (
            SELECT 1 FROM fact_evidence AS evidence WHERE evidence.fact_id = fact.id
        ))
        OR EXISTS (
            SELECT 1
            FROM fact_evidence AS evidence
            JOIN provider_observation AS observation ON observation.id = evidence.observation_id
            JOIN provider_current_observation AS pointer ON pointer.observation_id = observation.id
              AND pointer.provider_record_id = observation.provider_record_id
            JOIN provider_record AS record ON record.id = observation.provider_record_id
            JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
            JOIN provider ON provider.id = namespace.provider_id
            WHERE evidence.fact_id = fact.id AND record.status = 'active'
              AND provider.redistribution_policy <> 'forbidden'
              AND (NOT :for_ai OR provider.ai_usage_policy = 'allowed')
        )
    )
"""


async def _media(
    session: AsyncSession, cluster: list[str], *, for_ai: bool
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="entity_media",
            alias="link",
            columns="asset.id AS asset_id, asset.url, link.purpose, asset.safety,"
            " asset.spoiler_level",
            record="asset.provider_record_id",
            extra_join="JOIN media_asset AS asset ON asset.id = link.asset_id",
        )
        + AI_SOURCE
        + " AND link.purpose IN ('poster', 'cover')"
        + " ORDER BY link.id",
        {"ids": cluster, "for_ai": for_ai},
    )
    visible = [
        row
        for row in rows
        if row.safety not in {"explicit", "suggestive"} and row.spoiler_level <= 0
    ]
    return [
        {
            "asset_id": str(row.asset_id),
            "url": row.url,
            "purpose": row.purpose,
            "safety": row.safety,
        }
        for row in visible[:MAX_MEDIA]
    ]


async def _names(
    session: AsyncSession, cluster: list[str], *, for_ai: bool
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="entity_name",
            alias="name",
            columns="name.id, name.text, name.language, name.script, name.kind,"
            " name.is_official, name.is_original",
            record="name.provider_record_id",
        )
        + AI_SOURCE
        + " AND (NOT :for_ai OR NOT name.is_machine_generated)"
        + " ORDER BY name.kind, name.language, name.text, name.id",
        {"ids": cluster, "for_ai": for_ai},
    )
    return [
        {
            "id": row.id,
            "text": row.text,
            "language": row.language,
            "script": row.script,
            "kind": row.kind,
            "is_official": row.is_official,
            "is_original": row.is_original,
        }
        for row in rows[:MAX_NAMES]
    ]


async def _descriptions(
    session: AsyncSession, cluster: list[str], language: str, *, for_ai: bool
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="entity_description",
            alias="description",
            columns="description.id, description.language, description.text,"
            " description.is_official, description.spoiler_level,"
            " description.safety",
            record="description.provider_record_id",
        )
        + AI_SOURCE
        + " AND (NOT :for_ai OR NOT description.is_machine_generated)"
        + " ORDER BY (description.language = :language) DESC,"
        " description.language, description.id",
        {"ids": cluster, "language": language, "for_ai": for_ai},
    )
    visible = [
        row
        for row in rows
        if row.safety not in {"explicit", "suggestive"} and row.spoiler_level <= 0
    ]
    return [
        {
            "id": row.id,
            "language": row.language,
            "text": row.text[:DESCRIPTION_CHARS],
            "is_official": row.is_official,
        }
        for row in visible[:MAX_DESCRIPTIONS]
    ]


async def _fields(session: AsyncSession, root: UUID, *, for_ai: bool) -> list[dict[str, Any]]:
    decisions = await fetch(
        session,
        f"""
        SELECT decision.predicate_id, decision.language, fact.id, fact.value,
               fact.confidence, predicate.slug
        FROM resolution_decision AS decision
        JOIN fact ON fact.id = decision.selected_fact_id
        JOIN predicate ON predicate.id = decision.predicate_id
        WHERE decision.entity_id = CAST(:root AS uuid) AND decision.is_active
          {FACT_POLICY}
        ORDER BY predicate.slug, decision.language
        """,
        {"root": str(root), "for_ai": for_ai},
    )
    predicate_ids = [row.predicate_id for row in decisions]
    alternates: dict[int, list[dict[str, Any]]] = {}
    if predicate_ids:
        rivals = await fetch(
            session,
            f"""
            SELECT fact.id, fact.predicate_id, fact.value, fact.language,
                   fact.confidence
            FROM fact
            WHERE fact.predicate_id = ANY(CAST(:pids AS bigint[]))
              AND fact.entity_id = CAST(:root AS uuid)
              AND fact.status <> 'rejected'
              {FACT_POLICY}
              AND NOT EXISTS (
                SELECT 1 FROM resolution_decision AS decision
                WHERE decision.entity_id = fact.entity_id
                  AND decision.predicate_id = fact.predicate_id
                  AND decision.language = fact.language
                  AND decision.is_active
                  AND decision.selected_fact_id = fact.id
              )
            ORDER BY fact.predicate_id, fact.confidence DESC, fact.id
            """,
            {"pids": predicate_ids, "root": str(root), "for_ai": for_ai},
        )
        for rival in rivals:
            bucket = alternates.setdefault(rival.predicate_id, [])
            if len(bucket) >= MAX_ALTERNATES:
                continue
            bucket.append(
                {
                    "fact_id": str(rival.id),
                    "value": rival.value,
                    "language": rival.language,
                    "confidence": float(rival.confidence),
                }
            )
    return [
        {
            "predicate": row.slug,
            "language": row.language,
            "fact_id": str(row.id),
            "value": row.value,
            "confidence": float(row.confidence),
            "alternates": alternates.get(row.predicate_id, []),
        }
        for row in decisions
    ]


async def build_bundle(
    session: AsyncSession,
    *,
    root: UUID,
    cluster_ids: list[str],
    language: str = "",
    for_ai: bool = False,
) -> dict[str, Any]:
    summary = await entity_summary(session, root=root, cluster_ids=cluster_ids, language=language)
    if for_ai and (summary["entity_type"] != "work" or summary["lifecycle"] != "active"):
        raise ValueError("Metadata model input requires an active work.")
    bundle: dict[str, Any] = {
        "bundle_version": BUNDLE_VERSION,
        "language": language,
        "entity": {
            "id": summary["id"],
            "entity_type": summary["entity_type"],
            "audience": summary["audience"],
            "work_type": summary["work_type"],
        },
        "names": await _names(session, cluster_ids, for_ai=for_ai),
        "descriptions": await _descriptions(session, cluster_ids, language, for_ai=for_ai),
        "fields": await _fields(session, root, for_ai=for_ai),
        "media": await _media(session, cluster_ids, for_ai=for_ai),
        "ai_evidence": for_ai,
    }
    canonical = json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "bundle": bundle,
        "input_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
