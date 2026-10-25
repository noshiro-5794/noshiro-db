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

from .fragments import CURRENT, current_rows, fetch
from .summary import entity_summary

BUNDLE_VERSION = "v1"

MAX_NAMES = 20
MAX_DESCRIPTIONS = 3
MAX_CREDITS = 20
MAX_RELATIONS = 20
MAX_MEDIA = 6
MAX_ALTERNATES = 2
DESCRIPTION_CHARS = 1500

# Values produced by other sites' users rather than by the work. They may rank a
# listing internally and must never reach a page, so the generator never sees
# them. The set shrinks to nothing once metric extraction stops writing these
# predicates as facts.
SIGNAL_PREDICATES = frozenset(
    {
        "mal-score",
        "mal-rank",
        "mal-members",
        "mal-popularity",
        "anilist-average-score",
        "anilist-favourites",
        "anilist-popularity",
        "anilist-trending",
        "comment-count",
        "playtime-votes",
    }
)


async def _names(session: AsyncSession, cluster: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        current_rows(
            table="entity_name",
            alias="name",
            columns="name.id, name.text, name.language, name.script, name.kind,"
            " name.is_official, name.is_original",
            record="name.provider_record_id",
        )
        + " ORDER BY name.kind, name.language, name.text, name.id",
        {"ids": cluster},
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
    session: AsyncSession, cluster: list[str], language: str
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
        + " ORDER BY (description.language = :language) DESC,"
        " description.language, description.id",
        {"ids": cluster, "language": language},
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


async def _fields(session: AsyncSession, root: UUID) -> list[dict[str, Any]]:
    decisions = await fetch(
        session,
        """
        SELECT decision.predicate_id, decision.language, fact.id, fact.value,
               fact.confidence, predicate.slug
        FROM resolution_decision AS decision
        JOIN fact ON fact.id = decision.selected_fact_id
        JOIN predicate ON predicate.id = decision.predicate_id
        WHERE decision.entity_id = CAST(:root AS uuid) AND decision.is_active
        ORDER BY predicate.slug, decision.language
        """,
        {"root": str(root)},
    )
    predicate_ids = [row.predicate_id for row in decisions]
    alternates: dict[int, list[dict[str, Any]]] = {}
    if predicate_ids:
        rivals = await fetch(
            session,
            """
            SELECT fact.id, fact.predicate_id, fact.value, fact.language,
                   fact.confidence
            FROM fact
            WHERE fact.predicate_id = ANY(CAST(:pids AS bigint[]))
              AND fact.entity_id = CAST(:root AS uuid)
              AND fact.status <> 'rejected'
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
            {"pids": predicate_ids, "root": str(root)},
        )
        for rival in rivals:
            bucket = alternates.setdefault(rival.predicate_id, [])
            if len(bucket) >= MAX_ALTERNATES:
                continue
            bucket.append(
                {
                    "fact_id": rival.id,
                    "value": rival.value,
                    "language": rival.language,
                    "confidence": float(rival.confidence),
                }
            )
    return [
        {
            "predicate": row.slug,
            "language": row.language,
            "fact_id": row.id,
            "value": row.value,
            "confidence": float(row.confidence),
            "alternates": alternates.get(row.predicate_id, []),
        }
        for row in decisions
        if row.slug not in SIGNAL_PREDICATES
    ]


async def _credits(session: AsyncSession, cluster: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        """
        SELECT credit.role, credit.credited_as, credit.contributor_id
        FROM credit
        LEFT JOIN provider_observation AS observation
          ON observation.id = credit.observation_id
        LEFT JOIN provider_record AS record ON record.id = observation.provider_record_id
        WHERE credit.work_id = ANY(CAST(:ids AS uuid[]))
          AND {current}
        ORDER BY credit.role, credit.id
        LIMIT :limit
        """.format(
            current=CURRENT.format(
                record="observation.provider_record_id",
                observation="credit.observation_id",
            )
        ),
        {"ids": cluster, "limit": MAX_CREDITS},
    )
    return [
        {
            "role": row.role,
            "credited_as": row.credited_as,
            "contributor_id": str(row.contributor_id),
        }
        for row in rows
    ]


async def _relations(session: AsyncSession, cluster: list[str]) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        """
        SELECT relation.relation_type, relation.to_entity_id
        FROM entity_relation AS relation
        WHERE relation.from_entity_id = ANY(CAST(:ids AS uuid[]))
        ORDER BY relation.relation_type, relation.id
        LIMIT :limit
        """,
        {"ids": cluster, "limit": MAX_RELATIONS},
    )
    return [
        {
            "relation_type": row.relation_type,
            "to_entity_id": str(row.to_entity_id),
        }
        for row in rows
    ]


async def build_bundle(
    session: AsyncSession,
    *,
    root: UUID,
    cluster_ids: list[str],
    language: str = "",
) -> dict[str, Any]:
    summary = await entity_summary(session, root=root, cluster_ids=cluster_ids, language=language)
    bundle: dict[str, Any] = {
        "bundle_version": BUNDLE_VERSION,
        "language": language,
        "entity": {
            "id": summary["id"],
            "entity_type": summary["entity_type"],
            "audience": summary["audience"],
            "work_type": summary["work_type"],
        },
        "names": await _names(session, cluster_ids),
        "descriptions": await _descriptions(session, cluster_ids, language),
        "fields": await _fields(session, root),
        "credits": await _credits(session, cluster_ids),
        "relations": await _relations(session, cluster_ids),
        "media": summary["media"][:MAX_MEDIA],
    }
    canonical = json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "bundle": bundle,
        "input_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
