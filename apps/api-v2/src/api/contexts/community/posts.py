"""The public post feed, one payload shape for the list and the detail."""

from __future__ import annotations

import json
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


BLANK = "Post content can not be blank."
VISIBILITIES = ("public", "private", "followers")


async def create_post(
    session: AsyncSession, *, user_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    errors: dict[str, list[str]] = {}
    content = body.get("content")
    if not isinstance(content, str):
        errors["content"] = ["This field is required."]
    elif not content.strip():
        errors["content"] = [BLANK]
    elif len(content) > 10000:
        errors["content"] = ["Ensure this field has no more than 10000 characters."]
    visibility = body.get("visibility", "public")
    if visibility not in VISIBILITIES:
        errors["visibility"] = [f'"{visibility}" is not a valid choice.']
    if errors:
        raise ValueError(errors)
    entity_id = body.get("entity_id")
    if entity_id is not None:
        entity = await fetch(
            session,
            "SELECT id FROM entity WHERE id = CAST(:id AS uuid)"
            " AND lifecycle = 'active' AND visibility = 'public'",
            {"id": str(entity_id)},
        )
        if not entity:
            raise FileNotFoundError(entity_id)
    is_spoiler = bool(body.get("is_spoiler", False))
    is_nsfw = bool(body.get("is_nsfw", False))
    rows = await fetch(
        session,
        """
        INSERT INTO community_post (
            post_type, content, visibility, feed_policy, is_spoiler, is_nsfw,
            is_pinned, is_locked, reply_count, reaction_count, last_activity_at,
            created_at, updated_at, metadata, author_id, entity_id
        ) VALUES (
            :post_type, :content, :visibility, 'normal', :spoiler, :nsfw,
            false, false, 0, 0, now(), now(), now(), '{}'::jsonb, :author,
            CAST(:entity AS uuid)
        ) RETURNING id
        """,
        {
            "post_type": "entity" if entity_id is not None else "status",
            "content": content,
            "visibility": visibility,
            "spoiler": is_spoiler,
            "nsfw": is_nsfw,
            "author": user_id,
            "entity": str(entity_id) if entity_id is not None else None,
        },
    )
    post_id = rows[0].id
    await fetch(
        session,
        """
        INSERT INTO community_activity (
            user_id, entity_id, activity_type, post_id, message, visibility,
            feed_policy, group_key, dedupe_key, metadata, created_at
        ) VALUES (
            :author, CAST(:entity AS uuid), 'post_created', :post, 'Posted a status',
            :visibility, 'normal', :group_key, :dedupe_key,
            CAST(:metadata AS jsonb), now()
        )
        ON CONFLICT (dedupe_key) WHERE dedupe_key <> '' DO NOTHING RETURNING id
        """,
        {
            "author": user_id,
            "entity": str(entity_id) if entity_id is not None else None,
            "post": post_id,
            "visibility": visibility,
            "group_key": f"post:{user_id}",
            "dedupe_key": f"post_created:{post_id}",
            "metadata": json.dumps(
                {
                    "post": {
                        "id": post_id,
                        "entity_id": str(entity_id) if entity_id is not None else None,
                    }
                }
            ),
        },
    )
    await session.commit()
    return await post_by_id(session, viewer_id=user_id, post_id=post_id)


async def post_by_id(session: AsyncSession, *, viewer_id: int, post_id: int) -> dict[str, Any]:
    rows = await fetch(
        session,
        f"SELECT {POST_COLUMNS}, {VIEWER} FROM community_post AS post {JOINS} WHERE post.id = :id",
        {"id": post_id, "viewer": viewer_id},
    )
    if not rows:
        raise LookupError(post_id)
    return await post_payload(session, rows[0])


async def public_post(session: AsyncSession, *, viewer_id: int, post_id: int) -> dict[str, Any]:
    rows = await fetch(
        session,
        f"SELECT {POST_COLUMNS}, {VIEWER} FROM community_post AS post {JOINS}"
        " WHERE post.id = :id AND post.visibility = 'public'"
        " AND post.feed_policy <> 'hidden'"
        " AND post.author_id NOT IN ("
        "   SELECT blocked_user_id FROM community_user_block WHERE user_id = :viewer)"
        " AND post.author_id NOT IN ("
        "   SELECT user_id FROM community_user_block WHERE blocked_user_id = :viewer)",
        {"id": post_id, "viewer": viewer_id},
    )
    if not rows:
        raise LookupError(post_id)
    return await post_payload(session, rows[0])


async def _mine(session: AsyncSession, user_id: int, post_id: int) -> Any:
    rows = await fetch(
        session,
        "SELECT id, is_locked, feed_policy FROM community_post"
        " WHERE id = :id AND author_id = :author",
        {"id": post_id, "author": user_id},
    )
    if not rows:
        raise LookupError(post_id)
    return rows[0]


async def update_post(
    session: AsyncSession, *, user_id: int, post_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    row = await _mine(session, user_id, post_id)
    if row.is_locked or row.feed_policy == "hidden":
        raise PermissionError(post_id)
    errors: dict[str, list[str]] = {}
    sets: list[str] = []
    params: dict[str, Any] = {"id": post_id}
    if "content" in body:
        content = body["content"]
        if not isinstance(content, str):
            errors["content"] = ["Not a valid string."]
        elif not content.strip():
            errors["content"] = [BLANK]
        elif len(content) > 10000:
            errors["content"] = ["Ensure this field has no more than 10000 characters."]
        else:
            sets.append("content = :content")
            params["content"] = content
    if "visibility" in body:
        visibility = body["visibility"]
        if visibility not in VISIBILITIES:
            errors["visibility"] = [f'"{visibility}" is not a valid choice.']
        else:
            sets.append("visibility = :visibility")
            params["visibility"] = visibility
    for name in ("is_spoiler", "is_nsfw"):
        if name in body:
            sets.append(f"{name} = :{name}")
            params[name] = bool(body[name])
    if errors:
        raise ValueError(errors)
    if not sets:
        raise KeyError("no fields")
    await fetch(
        session,
        "UPDATE community_post SET " + ", ".join(sets) + ", updated_at = now()"
        " WHERE id = :id RETURNING id",
        params,
    )
    await session.commit()
    return await post_by_id(session, viewer_id=user_id, post_id=post_id)


async def delete_post(session: AsyncSession, *, user_id: int, post_id: int) -> None:
    await _mine(session, user_id, post_id)
    await fetch(
        session,
        "DELETE FROM community_activity WHERE post_id = :id RETURNING id",
        {"id": post_id},
    )
    await fetch(session, "DELETE FROM community_post WHERE id = :id RETURNING id", {"id": post_id})
    await session.commit()
