"""The comments under a post, oldest first."""

from __future__ import annotations

import json
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


VISIBILITIES = ("public", "private", "followers")
REPLY_COUNTED = ("post", "comment")


async def _comment_row(session: AsyncSession, *, viewer_id: int, comment_id: int) -> Any:
    rows = await fetch(
        session, QUERY + " WHERE comment.id = :id", {"id": comment_id, "viewer": viewer_id}
    )
    if not rows:
        raise LookupError(comment_id)
    return rows[0]


async def create_comment(
    session: AsyncSession,
    *,
    user_id: int,
    target_type: str,
    target_id: int,
    body: dict[str, Any],
) -> dict[str, Any]:
    from api.contexts.community.visibility import visible

    errors: dict[str, list[str]] = {}
    content = body.get("content")
    if not isinstance(content, str):
        errors["content"] = ["This field is required."]
    elif not content.strip():
        errors["content"] = ["Comment content can not be blank."]
    elif len(content) > 10000:
        errors["content"] = ["Ensure this field has no more than 10000 characters."]
    visibility = body.get("visibility", "public")
    if visibility not in VISIBILITIES:
        errors["visibility"] = [f'"{visibility}" is not a valid choice.']
    if errors:
        raise ValueError(errors)
    if not await visible(session, target_type, target_id):
        raise FileNotFoundError(target_id)
    parent_id = body.get("parent_id")
    entity = await fetch(
        session,
        "SELECT entity_id FROM community_post WHERE id = :id",
        {"id": target_id},
    )
    if parent_id is not None:
        parent = await fetch(
            session,
            "SELECT id, parent_id FROM community_comment"
            f" WHERE id = :id AND {target_type}_id = :target_id",
            {"id": parent_id, "target_id": target_id},
        )
        if not parent:
            raise LookupError(parent_id)
    created = await fetch(
        session,
        """
        INSERT INTO community_comment (
            content, visibility, is_spoiler, is_hidden, is_locked, reply_count,
            reaction_count, created_at, updated_at, metadata, author_id, parent_id,
        """
        + f" {target_type}_id"
        + """
        ) VALUES (
            :content, :visibility, :spoiler, false, false, 0, 0, now(), now(),
            '{}'::jsonb, :author, :parent,
        """
        + " :target_id"
        + """
        ) RETURNING id
        """,
        {
            "content": content,
            "visibility": visibility,
            "spoiler": bool(body.get("is_spoiler", False)),
            "author": user_id,
            "parent": parent_id,
            "target_id": target_id,
        },
    )
    comment_id = created[0].id
    if target_type in REPLY_COUNTED:
        table = "community_post" if target_type == "post" else "community_comment"
        await fetch(
            session,
            f"UPDATE {table} SET reply_count = reply_count + 1 WHERE id = :id RETURNING id",
            {"id": target_id},
        )
    if parent_id is not None:
        await fetch(
            session,
            "UPDATE community_comment SET reply_count = reply_count + 1"
            " WHERE id = :id RETURNING id",
            {"id": parent_id},
        )
    await fetch(
        session,
        """
        INSERT INTO community_activity (
            user_id, entity_id, activity_type, comment_id, message, visibility,
            feed_policy, group_key, dedupe_key, metadata, created_at
        ) VALUES (
            :author, CAST(:entity AS uuid), 'comment_created', :comment,
            :message, :visibility, 'normal', :group_key, :dedupe_key,
            CAST(:metadata AS jsonb), now()
        )
        ON CONFLICT (dedupe_key) WHERE dedupe_key <> '' DO NOTHING RETURNING id
        """,
        {
            "author": user_id,
            "entity": str(entity[0].entity_id) if entity and entity[0].entity_id else None,
            "comment": comment_id,
            "message": f"Commented on a {target_type}",
            "visibility": visibility,
            "group_key": f"{target_type}_comment:{target_id}",
            "dedupe_key": f"comment_created:{comment_id}",
            "metadata": json.dumps(
                {"target": {"type": target_type, "id": target_id}, "comment": {"id": comment_id}}
            ),
        },
    )
    await session.commit()
    return await comment_payload(
        await _comment_row(session, viewer_id=user_id, comment_id=comment_id)
    )
