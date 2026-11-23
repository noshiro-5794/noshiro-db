"""Read the work's published metadata against current evidence."""

from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch

from .provenance import CURRENT, DESCRIPTION_CHARS, PROVENANCE_JOINS, current_rows, visible


async def profile(
    session: AsyncSession, *, entity_id: UUID, members: list[str], language: str
) -> Any | None:
    rows = await fetch(
        session,
        f"""
        SELECT profile.* FROM entity_metadata_publication AS publication
        JOIN entity_metadata_revision AS profile ON profile.id = publication.revision_id
        JOIN entity AS entity ON entity.id = profile.entity_id AND entity.kind = 'work'
        JOIN entity_name AS name ON name.id = profile.title_name_id
        {
            PROVENANCE_JOINS.format(
                record="name.provider_record_id", observation="name.observation_id"
            )
        }
        WHERE publication.entity_id = :entity AND publication.language = :language
          AND profile.state = 'approved'
          AND name.entity_id = ANY(CAST(:members AS uuid[]))
          AND name.text = profile.title_text
          AND (NOT profile.is_machine_generated OR provider.ai_usage_policy = 'allowed')
          AND {CURRENT.format(record="name.provider_record_id", observation="name.observation_id")}
        """,
        {"entity": entity_id, "members": members, "language": language},
    )
    return rows[0] if rows else None


async def description(
    session: AsyncSession, *, entity_id: UUID, members: list[str], language: str
) -> dict[str, Any] | None:
    current = await profile(session, entity_id=entity_id, members=members, language=language)
    if current is None or not current.description_text:
        return None
    rows = await fetch(
        session,
        current_rows(
            table="entity_description",
            alias="description",
            columns="description.text, description.safety, description.spoiler_level, "
            "citation.evidence_hash, (SELECT count(*) FROM entity_metadata_citation "
            "WHERE revision_id = :revision) AS citation_count",
            record="description.provider_record_id",
            extra_join="JOIN entity_metadata_citation AS citation "
            "ON citation.description_id = description.id AND citation.revision_id = :revision",
        )
        + " AND (NOT :machine OR provider.ai_usage_policy = 'allowed')",
        {
            "ids": members,
            "revision": current.id,
            "machine": current.is_machine_generated,
        },
    )
    if not rows or len(rows) != rows[0].citation_count:
        return None
    if any(
        not visible(row, content_allowed=True)
        or sha256(row.text[:DESCRIPTION_CHARS].encode("utf-8")).hexdigest() != row.evidence_hash
        for row in rows
    ):
        return None
    if not current.is_machine_generated and not any(
        row.text.startswith(current.description_text) for row in rows
    ):
        return None
    return {
        "text": current.description_text,
        "language": current.language,
        "is_official": False,
        "is_machine_generated": current.is_machine_generated,
        "is_reviewed": current.reviewed_at is not None,
        "spoiler_level": 0,
        "safety": "safe",
        "provenance": None,
    }
