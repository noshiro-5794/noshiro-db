"""The comments under a post, oldest first."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch, isoformat

from .people import person

QUERY = """
    SELECT comment.id, comment.parent_id, comment.content, comment.visibility,
           comment.is_spoiler, comment.is_hidden, comment.is_locked,
           comment.reply_count, comment.reaction_count,
           comment.created_at, comment.updated_at,
           comment.post_id, comment.review_id, comment.collection_id,
           author.id AS author_id, author_profile.nickname AS author_nickname,
           author_profile.avatar AS author_avatar,
           EXISTS (SELECT 1 FROM community_reaction AS reaction
                    WHERE reaction.comment_id = comment.id
                      AND reaction.reaction_type = 'like'
                      AND reaction.user_id = :viewer) AS has_liked,
           EXISTS (SELECT 1 FROM community_user_follow AS follow
                    WHERE follow.follower_id = :viewer
                      AND follow.following_id = comment.author_id)
             AS is_following_author
    FROM community_comment AS comment
    JOIN "user" AS author ON author.id = comment.author_id
    LEFT JOIN user_profile AS author_profile ON author_profile.user_id = author.id
"""

TARGETS = ("post", "review", "collection")


def _target(row: Any) -> dict[str, Any] | None:
    for kind in TARGETS:
        target_id = getattr(row, f"{kind}_id", None)
        if target_id is not None:
            return {"type": kind, "id": target_id}
    return None


async def comment_payload(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "parent_id": row.parent_id,
        "target": _target(row),
        "content": row.content,
        "visibility": row.visibility,
        "is_spoiler": row.is_spoiler,
        "is_hidden": row.is_hidden,
        "is_locked": row.is_locked,
        "reply_count": row.reply_count,
        "reaction_count": row.reaction_count,
        "created_at": isoformat(row.created_at),
        "updated_at": isoformat(row.updated_at),
        "author": (
            None if row.is_hidden else person(row.author_id, row.author_nickname, row.author_avatar)
        ),
        "viewer_state": {
            "has_liked": bool(row.has_liked),
            "is_following_author": bool(row.is_following_author),
        },
    }


async def list_comments(
    session: AsyncSession,
    *,
    viewer_id: int,
    target_type: str,
    target_id: int,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    clauses = [
        f"comment.{target_type}_id = :target_id",
        "comment.visibility = 'public'",
        "(comment.is_hidden = false OR comment.reply_count > 0)",
        """comment.author_id NOT IN (
            SELECT blocked_user_id FROM community_user_block WHERE user_id = :viewer)""",
        """comment.author_id NOT IN (
            SELECT user_id FROM community_user_block WHERE blocked_user_id = :viewer)""",
    ]
    params: dict[str, Any] = {"target_id": target_id, "viewer": viewer_id}
    clause = " AND ".join(clauses)
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM community_comment AS comment WHERE {clause}",
        params,
    )
    rows = await fetch(
        session,
        QUERY + f" WHERE {clause}" + " ORDER BY comment.created_at ASC, comment.id ASC"
        " LIMIT :limit OFFSET :offset",
        {
            **params,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    return int(total[0].total), [await comment_payload(row) for row in rows]
