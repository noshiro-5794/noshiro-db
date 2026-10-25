"""Validation and storage of a display proposal.

The generator proposes; this module decides whether the proposal may become a
page. The checks are deterministic: every cited id must exist in the bundle, a
rewritten description may not introduce a number that no cited fact contains,
and a rejected proposal is stored as rejected rather than silently dropped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import fetch

MAX_DESCRIPTION_CHARS = 2000
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
CJK = ("zh", "ja", "ko")


@dataclass(slots=True)
class DisplayProposal:
    title_name_id: int
    description_text: str = ""
    description_source_ids: list[int] = field(default_factory=list)
    cover_asset_id: str | None = None
    field_choices: list[dict[str, Any]] = field(default_factory=list)
    is_machine_generated: bool = False
    confidence: float | None = None


def _field_fact_ids(bundle: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in bundle["fields"]:
        if item["fact_id"]:
            ids.add(item["fact_id"])
        for alternate in item["alternates"]:
            ids.add(alternate["fact_id"])
    return ids


def _cited_values(bundle: dict[str, Any], fact_ids: set[str]) -> str:
    parts: list[str] = []
    for item in bundle["fields"]:
        if item["fact_id"] in fact_ids:
            parts.append(str(item["value"]))
        for alternate in item["alternates"]:
            if alternate["fact_id"] in fact_ids:
                parts.append(str(alternate["value"]))
    return " ".join(parts)


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
        unknown = [
            value for value in proposal.description_source_ids if value not in description_ids
        ]
        if unknown:
            errors.append(f"description cites unknown rows: {unknown}")
        if len(proposal.description_text) > MAX_DESCRIPTION_CHARS:
            errors.append("description is too long")
        cited = (
            _cited_values(bundle, set())
            + " "
            + _description_values(bundle, proposal.description_source_ids)
        )
        numbers = {token for token in NUMBER.findall(proposal.description_text)}
        missing = [token for token in numbers if token not in cited]
        if missing:
            errors.append(f"description states numbers no fact supports: {missing}")

    facts = _field_fact_ids(bundle)
    for choice in proposal.field_choices:
        if choice.get("fact_id") not in facts:
            errors.append(f"choice cites unknown fact: {choice.get('fact_id')}")

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
) -> tuple[int, str]:
    """Store the proposal as a draft, or as rejected with its reasons."""
    entity = bundle["entity"]["id"]
    language = bundle["language"]
    title = next(item for item in bundle["names"] if item["id"] == proposal.title_name_id)
    errors = validate(bundle, proposal, language=language)
    rows = await fetch(
        session,
        """
        INSERT INTO entity_display_profile (
            entity_id, language, title_name_id, title_text, description_text,
            description_source_ids, is_machine_generated, cover_asset_id,
            field_choices, bundle_version, input_hash, model, prompt_version,
            confidence, state, reject_reason
        ) VALUES (
            CAST(:entity AS uuid), :language, :title_name_id, :title_text,
            :description_text, CAST(:source_ids AS jsonb), :machine,
            CAST(:cover AS uuid), CAST(:choices AS jsonb), :bundle_version,
            :input_hash, :model, :prompt_version, :confidence, :state, :reason
        )
        ON CONFLICT (entity_id, language, input_hash) DO UPDATE SET
            title_name_id = EXCLUDED.title_name_id,
            title_text = EXCLUDED.title_text,
            description_text = EXCLUDED.description_text,
            description_source_ids = EXCLUDED.description_source_ids,
            cover_asset_id = EXCLUDED.cover_asset_id,
            field_choices = EXCLUDED.field_choices,
            model = EXCLUDED.model,
            prompt_version = EXCLUDED.prompt_version,
            confidence = EXCLUDED.confidence,
            state = EXCLUDED.state,
            reject_reason = EXCLUDED.reject_reason,
            updated_at = now()
        RETURNING id, state
        """,
        {
            "entity": entity,
            "language": language,
            "title_name_id": proposal.title_name_id,
            "title_text": title["text"],
            "description_text": proposal.description_text,
            "source_ids": json.dumps(proposal.description_source_ids),
            "machine": proposal.is_machine_generated,
            "cover": proposal.cover_asset_id,
            "choices": json.dumps(proposal.field_choices, ensure_ascii=False),
            "bundle_version": bundle["bundle_version"],
            "input_hash": input_hash,
            "model": model,
            "prompt_version": prompt_version,
            "confidence": proposal.confidence,
            "state": "rejected" if errors else "draft",
            "reason": "; ".join(errors),
        },
    )
    row = rows[0]
    return int(row.id), str(row.state)


async def activate(
    session: AsyncSession, *, entity_id: UUID, language: str, input_hash: str
) -> int | None:
    """Promote one draft to the live profile, archiving the previous one.

    Two statements in one transaction: the unique index allows a single active
    row per entity and language, so the old one has to leave first.
    """
    await fetch(
        session,
        """
        UPDATE entity_display_profile
        SET state = 'archived', updated_at = now()
        WHERE entity_id = CAST(:entity AS uuid)
          AND language = :language
          AND state = 'active'
        RETURNING id
        """,
        {"entity": str(entity_id), "language": language},
    )
    rows = await fetch(
        session,
        """
        UPDATE entity_display_profile
        SET state = 'active', updated_at = now()
        WHERE entity_id = CAST(:entity AS uuid)
          AND language = :language
          AND input_hash = :input_hash
          AND state = 'draft'
        RETURNING id
        """,
        {"entity": str(entity_id), "language": language, "input_hash": input_hash},
    )
    return int(rows[0].id) if rows else None
