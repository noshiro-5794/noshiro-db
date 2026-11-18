"""Whether a target may be seen, and therefore interacted with.

A target that exists but is private is a 404, not a 403: the caller must not learn
that it exists. Each type carries its own rule, taken from the old service.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

VISIBLE = {
    "post": "SELECT 1 FROM community_post WHERE id = :id"
    " AND visibility = 'public' AND feed_policy <> 'hidden'",
    "comment": "SELECT 1 FROM community_comment WHERE id = :id"
    " AND visibility = 'public' AND is_hidden = false",
    "review": "SELECT 1 FROM user_review AS review"
    " JOIN user_library_entry AS entry ON entry.id = review.user_subject_id"
    " WHERE review.id = :id AND review.is_public AND entry.is_public"
    " AND entry.entity_id IS NOT NULL",
    "collection": "SELECT 1 FROM user_collection WHERE id = :id AND is_public",
    "activity": "SELECT 1 FROM community_activity WHERE id = :id AND visibility = 'public'",
}


async def visible(session: AsyncSession, kind: str, target_id: Any) -> bool:
    rows = await fetch(session, VISIBLE[kind], {"id": target_id})
    return bool(rows)
