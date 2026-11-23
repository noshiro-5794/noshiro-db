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

from .provenance import DESCRIPTION_CHARS, current_rows
from .summary import entity_summary

BUNDLE_VERSION = "v3"

MAX_NAMES = 20
MAX_DESCRIPTIONS = 3
MAX_MEDIA = 6
AI_SOURCE = " AND (NOT :for_ai OR provider.ai_usage_policy = 'allowed')"


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
        "media": await _media(session, cluster_ids, for_ai=for_ai),
        "ai_evidence": for_ai,
    }
    canonical = json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "bundle": bundle,
        "input_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
