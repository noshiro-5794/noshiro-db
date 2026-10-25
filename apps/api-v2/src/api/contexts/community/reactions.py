"""A reaction, the count it bumps and the notification it sends.

Only posts and comments carry a counter; the other targets accept the reaction
without one, which is what the old service does. Removing a reaction does not
decrement — that is also what the old service does, and the drift is recorded as
a known divergence rather than silently fixed.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.community.visibility import visible
from api.contexts.presentation.fragments import fetch, isoformat

TARGETS = ("post", "comment", "review", "collection", "activity")
REACTIONS = ("like", "useful", "agree")
COUNTED = ("post", "comment")
UNSUPPORTED_TARGET = "Unsupported target type."
UNSUPPORTED_REACTION = "Unsupported reaction type."


async def _owner(session: AsyncSession, kind: str, target_id: int) -> Any:
    if kind == "review":
        rows = await fetch(
            session,
            "SELECT entry.user_id FROM user_review AS review"
            " JOIN user_library_entry AS entry ON entry.id = review.user_subject_id"
            " WHERE review.id = :id",
            {"id": target_id},
        )
    elif kind == "comment":
        rows = await fetch(
            session,
            "SELECT author_id AS user_id FROM community_comment WHERE id = :id",
            {"id": target_id},
        )
    else:
        table = {
            "post": "community_post",
            "collection": "user_collection",
            "activity": "community_activity",
        }[kind]
        rows = await fetch(
            session, f"SELECT user_id FROM {table} WHERE id = :id", {"id": target_id}
        )
    return rows[0].user_id if rows else None


async def _payload(session: AsyncSession, reaction_id: int) -> dict[str, Any]:
    rows = await fetch(
        session,
        "SELECT id, reaction_type, created_at, post_id, comment_id, review_id,"
        " collection_id, activity_id FROM community_reaction WHERE id = :id",
        {"id": reaction_id},
    )
    row = rows[0]
    kind = next(name for name in TARGETS if getattr(row, f"{name}_id") is not None)
    return {
        "id": row.id,
        "target_type": kind,
        "target_id": getattr(row, f"{kind}_id"),
        "reaction_type": row.reaction_type,
        "created_at": isoformat(row.created_at),
    }


async def set_reaction(
    session: AsyncSession,
    *,
    user_id: int,
    target_type: str,
    target_id: int,
    reaction_type: str,
) -> tuple[dict[str, Any], bool]:
    if target_type not in TARGETS:
        raise ValueError({"target_type": UNSUPPORTED_TARGET})
    if reaction_type not in REACTIONS:
        raise ValueError({"reaction_type": UNSUPPORTED_REACTION})
    if not await visible(session, target_type, target_id):
        raise FileNotFoundError(target_id)
    existing = await fetch(
        session,
        "SELECT id FROM community_reaction WHERE user_id = :user_id"
        " AND reaction_type = :reaction_type"
        f" AND {target_type}_id = :target_id",
        {"user_id": user_id, "reaction_type": reaction_type, "target_id": target_id},
    )
    if existing:
        return await _payload(session, existing[0].id), False
    created = await fetch(
        session,
        "INSERT INTO community_reaction (user_id, reaction_type, created_at,"
        f" {target_type}_id) VALUES (:user_id, :reaction_type, now(), :target_id)"
        " RETURNING id",
        {"user_id": user_id, "reaction_type": reaction_type, "target_id": target_id},
    )
    if target_type in COUNTED:
        table = "community_post" if target_type == "post" else "community_comment"
        await fetch(
            session,
            f"UPDATE {table} SET reaction_count = reaction_count + 1 WHERE id = :id RETURNING id",
            {"id": target_id},
        )
    owner = await _owner(session, target_type, target_id)
    if owner is not None and owner != user_id:
        await fetch(
            session,
            "INSERT INTO community_notification (recipient_id, actor_id,"
            " notification_type, " + target_type + "_id, metadata, created_at)"
            " VALUES (:recipient, :actor, 'reacted', :target_id,"
            " CAST(:metadata AS jsonb), now()) RETURNING id",
            {
                "recipient": owner,
                "actor": user_id,
                "target_id": target_id,
                "metadata": json.dumps({"actor_id": user_id, "reaction_type": reaction_type}),
            },
        )
    await session.commit()
    return await _payload(session, created[0].id), True


async def remove_reaction(
    session: AsyncSession,
    *,
    user_id: int,
    target_type: str,
    target_id: int,
    reaction_type: str,
) -> None:
    if target_type not in TARGETS or reaction_type not in REACTIONS:
        return
    await fetch(
        session,
        "DELETE FROM community_reaction WHERE user_id = :user_id"
        " AND reaction_type = :reaction_type"
        f" AND {target_type}_id = :target_id RETURNING id",
        {"user_id": user_id, "reaction_type": reaction_type, "target_id": target_id},
    )
    await session.commit()
