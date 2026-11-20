"""The timeline entries a write fans out.

One shape per action: the metadata carries an entity snapshot so a feed row can
render without loading the work, and the dedupe key makes a retry harmless.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


async def _entity(session: AsyncSession, entity_id: str) -> Any:
    rows = await fetch(
        session,
        "SELECT entity.id, entity.kind, entity.audience,"
        " (SELECT name.text FROM entity_name AS name"
        "   WHERE name.entity_id = entity.id"
        "   ORDER BY name.is_official DESC, name.id LIMIT 1) AS display_name"
        " FROM entity WHERE entity.id = CAST(:id AS uuid)",
        {"id": entity_id},
    )
    return rows[0] if rows else None


async def create_review_activity(
    session: AsyncSession,
    *,
    user_id: int,
    entry_id: int,
    review_id: int,
    title: str,
    entry_is_public: bool,
    review_is_public: bool,
    entity_id: str,
) -> None:
    entity = await _entity(session, entity_id)
    if entity is None:
        return
    display_name = entity.display_name or "Untitled"
    is_public = entry_is_public and review_is_public
    metadata = {
        "entity": {
            "id": str(entity.id),
            "kind": entity.kind,
            "display_name": display_name,
            "audience": entity.audience,
        },
        "library_entry": {"id": entry_id},
        "review": {"id": review_id, "title": title},
    }
    await fetch(
        session,
        """
        INSERT INTO community_activity (
            user_id, entity_id, activity_type, user_subject_id, review_id,
            message, visibility, feed_policy, group_key, dedupe_key, metadata,
            created_at
        ) VALUES (
            :user_id, CAST(:entity AS uuid), 'review_created', :entry_id,
            :review_id, :message, :visibility, 'normal', :group_key,
            :dedupe_key, CAST(:metadata AS jsonb), now()
        )
        ON CONFLICT (dedupe_key) WHERE dedupe_key <> '' DO NOTHING
        RETURNING id
        """,
        {
            "user_id": user_id,
            "entity": entity_id,
            "entry_id": entry_id,
            "review_id": review_id,
            "message": f"Posted a review for '{display_name}': {title}",
            "visibility": "public" if is_public else "private",
            "group_key": f"review:{entity_id}",
            "dedupe_key": f"review_created:{review_id}",
            "metadata": json.dumps(metadata, ensure_ascii=False),
        },
    )
