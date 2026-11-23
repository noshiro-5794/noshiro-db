"""Validate, store, and publish versioned display proposals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, resolve
from api.db import fetch

from .bundle import build_bundle

MAX_DESCRIPTION_CHARS = 2000
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
CJK = ("zh", "ja", "ko")


@dataclass(slots=True)
class DisplayProposal:
    title_name_id: int
    description_text: str = ""
    description_source_ids: list[int] = field(default_factory=list)
    cover_asset_id: str | None = None
    is_machine_generated: bool = False
    confidence: float | None = None


def _description_values(bundle: dict[str, Any], ids: list[int]) -> str:
    return " ".join(item["text"] for item in bundle["descriptions"] if item["id"] in ids)


def validate(bundle: dict[str, Any], proposal: DisplayProposal, *, language: str = "") -> list[str]:
    """Return the reasons this proposal may not be published; empty means valid."""
    errors: list[str] = []
    names = {item["id"]: item for item in bundle["names"]}
    if proposal.title_name_id not in names:
        errors.append("title_name_id is not one of the bundle names")

    description_ids = {item["id"] for item in bundle["descriptions"]}
    if proposal.description_text:
        if not proposal.description_source_ids:
            errors.append("a description must cite source descriptions")
        unknown = [
            value for value in proposal.description_source_ids if value not in description_ids
        ]
        if unknown:
            errors.append(f"description cites unknown rows: {unknown}")
        if len(proposal.description_text) > MAX_DESCRIPTION_CHARS:
            errors.append("description is too long")
        cited = set(NUMBER.findall(_description_values(bundle, proposal.description_source_ids)))
        missing = sorted(set(NUMBER.findall(proposal.description_text)) - cited)
        if missing:
            errors.append(f"description states numbers no fact supports: {missing}")

    covers = {item["asset_id"] for item in bundle["media"]}
    if proposal.cover_asset_id is not None and proposal.cover_asset_id not in covers:
        errors.append("cover_asset_id is not one of the bundle covers")

    if language and proposal.description_text:
        first = language.split("-")[0].lower()
        if first in CJK and not re.search(
            r"[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]", proposal.description_text
        ):
            errors.append("description does not look like the requested language")
    return errors


async def submit(
    session: AsyncSession,
    *,
    bundle: dict[str, Any],
    proposal: DisplayProposal,
    input_hash: str,
    model: str,
    prompt_version: str,
    agent_step_id: UUID | None = None,
) -> tuple[int, str]:
    """Store a validated draft, preserving an already-published revision."""
    entity = bundle["entity"]["id"]
    language = bundle["language"]
    errors = validate(bundle, proposal, language=language)
    if errors:
        raise ValueError(" ".join(errors))
    title = next(item for item in bundle["names"] if item["id"] == proposal.title_name_id)
    rows = await fetch(
        session,
        """
        INSERT INTO entity_metadata_revision (
            entity_id, language, title_name_id, title_text, description_text,
            is_machine_generated, cover_asset_id, bundle_version, input_hash, model,
            prompt_version, confidence, agent_step_id
        ) VALUES (
            CAST(:entity AS uuid), :language, :title_name_id, :title_text, :description_text,
            :machine, CAST(:cover AS uuid), :bundle_version, :input_hash, :model,
            :prompt_version, :confidence, :step_id
        )
        ON CONFLICT (entity_id, language, input_hash) WHERE state = 'draft' DO UPDATE SET
            title_name_id = EXCLUDED.title_name_id,
            title_text = EXCLUDED.title_text,
            description_text = EXCLUDED.description_text,
            is_machine_generated = EXCLUDED.is_machine_generated,
            cover_asset_id = EXCLUDED.cover_asset_id,
            model = EXCLUDED.model,
            prompt_version = EXCLUDED.prompt_version,
            confidence = EXCLUDED.confidence,
            agent_step_id = EXCLUDED.agent_step_id,
            updated_at = now()
        RETURNING id, state
        """,
        {
            "entity": entity,
            "language": language,
            "title_name_id": proposal.title_name_id,
            "title_text": title["text"],
            "description_text": proposal.description_text,
            "machine": proposal.is_machine_generated,
            "cover": proposal.cover_asset_id,
            "bundle_version": bundle["bundle_version"],
            "input_hash": input_hash,
            "model": model,
            "prompt_version": prompt_version,
            "confidence": proposal.confidence,
            "step_id": agent_step_id,
        },
    )
    row = rows[0]
    await fetch(
        session,
        "DELETE FROM entity_metadata_citation WHERE revision_id = :id RETURNING position",
        {"id": row.id},
    )
    if proposal.description_text:
        texts = {item["id"]: item["text"] for item in bundle["descriptions"]}
        citations = list(dict.fromkeys(proposal.description_source_ids))
        await fetch(
            session,
            """
            INSERT INTO entity_metadata_citation
                (revision_id, position, description_id, evidence_hash)
            SELECT :id, citation.position, citation.description_id, citation.evidence_hash
            FROM unnest(CAST(:citations AS bigint[]), CAST(:hashes AS text[]))
                 WITH ORDINALITY AS citation(description_id, evidence_hash, position)
            RETURNING position
            """,
            {
                "id": row.id,
                "citations": citations,
                "hashes": [sha256(texts[value].encode("utf-8")).hexdigest() for value in citations],
            },
        )
    return int(row.id), str(row.state)


async def activate(
    session: AsyncSession,
    *,
    entity_id: UUID,
    language: str,
    input_hash: str,
    reviewed_by: int | None = None,
) -> int | None:
    """Approve an evidence-current draft and switch the publication pointer atomically."""
    await fetch(
        session, "SELECT id FROM entity WHERE id = :entity FOR UPDATE", {"entity": entity_id}
    )
    draft = await fetch(
        session,
        """
        SELECT id, is_machine_generated FROM entity_metadata_revision
        WHERE entity_id = :entity AND language = :language AND input_hash = :input_hash
          AND state = 'draft'
        FOR UPDATE
        """,
        {"entity": entity_id, "language": language, "input_hash": input_hash},
    )
    if not draft or await resolve(session, entity_id) != entity_id:
        return None
    members = await cluster_ids(session, entity_id)
    current = await build_bundle(
        session,
        root=entity_id,
        cluster_ids=sorted(map(str, members)),
        language=language,
        for_ai=draft[0].is_machine_generated,
    )
    if current["input_hash"] != input_hash:
        return None
    identifier = int(draft[0].id)
    await fetch(
        session,
        """
        UPDATE entity_metadata_revision
        SET state = 'approved', reviewed_at = now(), reviewed_by = :reviewer, updated_at = now()
        WHERE id = :id
        RETURNING id
        """,
        {"id": identifier, "reviewer": reviewed_by},
    )
    await fetch(
        session,
        """
        INSERT INTO entity_metadata_publication (entity_id, language, revision_id)
        VALUES (:entity, :language, :id)
        ON CONFLICT (entity_id, language) DO UPDATE
        SET revision_id = EXCLUDED.revision_id, published_at = EXCLUDED.published_at
        RETURNING revision_id
        """,
        {"entity": entity_id, "language": language, "id": identifier},
    )
    return identifier
