"""The public post feed, one payload shape for the list and the detail."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.fragments import fetch, isoformat
from api.contexts.presentation.summary import entity_summary

from .people import person

POST_COLUMNS = """
    post.id, post.post_type, post.content, post.visibility, post.feed_policy,
    post.is_spoiler, post.is_nsfw, post.is_pinned, post.is_locked,
    post.reply_count, post.reaction_count, post.last_activity_at,
    post.created_at, post.updated_at, post.entity_id,
    author.id AS author_id, author_profile.nickname AS author_nickname,
    author_profile.avatar AS author_avatar
"""

VIEWER = """
    EXISTS (SELECT 1 FROM community_reaction AS reaction
             WHERE reaction.post_id = post.id AND reaction.reaction_type = 'like'
               AND reaction.user_id = :viewer) AS has_liked,
    EXISTS (SELECT 1 FROM community_bookmark AS bookmark
             WHERE bookmark.post_id = post.id AND bookmark.user_id = :viewer)
             AS has_bookmarked,
    EXISTS (SELECT 1 FROM community_user_follow AS follow
             WHERE follow.follower_id = :viewer
               AND follow.following_id = post.author_id)
             AS is_following_author
"""

JOINS = """
    JOIN "user" AS author ON author.id = post.author_id
    LEFT JOIN user_profile AS author_profile ON author_profile.user_id = author.id
"""

EXCLUDED = """
    post.author_id NOT IN (
        SELECT blocked_user_id FROM community_user_block WHERE user_id = :viewer)
    AND post.author_id NOT IN (
        SELECT user_id FROM community_user_block WHERE blocked_user_id = :viewer)
    AND post.author_id NOT IN (
        SELECT muted_user_id FROM community_user_mute WHERE user_id = :viewer)
"""


async def post_payload(session: AsyncSession, row: Any) -> dict[str, Any]:
    entity = None
    if row.entity_id is not None:
        root = await resolve(session, row.entity_id) or row.entity_id
        cluster = await cluster_ids(session, root)
        entity = await entity_summary(
            session,
            root=root,
            cluster_ids=[str(value) for value in cluster],
            language="",
        )
    return {
        "id": row.id,
        "post_type": row.post_type,
        "content": row.content,
        "visibility": row.visibility,
        "feed_policy": row.feed_policy,
        "is_spoiler": row.is_spoiler,
        "is_nsfw": row.is_nsfw,
        "is_pinned": row.is_pinned,
        "is_locked": row.is_locked,
        "reply_count": row.reply_count,
        "reaction_count": row.reaction_count,
        "last_activity_at": isoformat(row.last_activity_at),
        "created_at": isoformat(row.created_at),
        "updated_at": isoformat(row.updated_at),
        "author": person(row.author_id, row.author_nickname, row.author_avatar),
        "entity": entity,
        "viewer_state": {
            "has_liked": bool(row.has_liked),
            "has_bookmarked": bool(row.has_bookmarked),
            "is_following_author": bool(row.is_following_author),
        },
    }


async def list_posts(
    session: AsyncSession,
    *,
    viewer_id: int,
    entity_id: str,
    keyword: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    clauses = ["post.visibility = 'public'", "post.feed_policy <> 'hidden'", EXCLUDED]
    params: dict[str, Any] = {"viewer": viewer_id}
    if entity_id:
        clauses.append("post.entity_id = CAST(:entity AS uuid)")
        params["entity"] = entity_id
    if keyword:
        clauses.append("post.content ILIKE :keyword")
        params["keyword"] = f"%{keyword}%"
    clause = " AND ".join(clauses)
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM community_post AS post WHERE {clause}",
        params,
    )
    rows = await fetch(
        session,
        f"SELECT {POST_COLUMNS}, {VIEWER} FROM community_post AS post {JOINS}"
        f" WHERE {clause}"
        " ORDER BY post.last_activity_at DESC, post.id DESC"
        " LIMIT :limit OFFSET :offset",
        {
            **params,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    return int(total[0].total), [await post_payload(session, row) for row in rows]
