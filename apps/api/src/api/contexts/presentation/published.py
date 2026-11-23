"""Read the work's published metadata against current evidence."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch

from .provenance import CURRENT, PROVENANCE_JOINS, current_rows, visible


async def profile(
    session: AsyncSession, *, entity_id: UUID, members: list[str], language: str
) -> Any | None:
    rows = await fetch(
        session,
        f"""
        SELECT profile.* FROM entity_display_profile AS profile
        JOIN entity AS entity ON entity.id = profile.entity_id AND entity.kind = 'work'
        JOIN entity_name AS name ON name.id = profile.title_name_id
        {
            PROVENANCE_JOINS.format(
                record="name.provider_record_id", observation="name.observation_id"
            )
        }
        WHERE profile.entity_id = :entity AND profile.language = :language
          AND profile.state = 'active'
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
    if current is None or not current.description_text or not current.description_source_ids:
        return None
    rows = await fetch(
        session,
        current_rows(
            table="entity_description",
            alias="description",
            columns="description.id, description.text, "
            "description.safety, description.spoiler_level",
            record="description.provider_record_id",
        )
        + " AND description.id = ANY(CAST(:citations AS bigint[]))"
        " AND (NOT :machine OR provider.ai_usage_policy = 'allowed')",
        {
            "ids": members,
            "citations": current.description_source_ids,
            "machine": current.is_machine_generated,
        },
    )
    safe = {row.id: row.text for row in rows if visible(row, content_allowed=True)}
    if set(safe) != set(current.description_source_ids):
        return None
    if not current.is_machine_generated and not any(
        text.startswith(current.description_text) for text in safe.values()
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
