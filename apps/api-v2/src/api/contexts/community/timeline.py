"""The timeline: one activity with every sub-object it can carry.

The entity a row shows is not always its own: an activity about a collection item
or a review has to borrow the work from the thing it points at. The fallback chain
is the same one the old serializer walks.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.fragments import fetch, isoformat
from api.contexts.presentation.summary import entity_summary
from api.shared.cursor import Cursor, position_of

from .people import person

ACTIVITY_QUERY = """
    SELECT activity.id, activity.activity_type, activity.message,
           activity.visibility, activity.feed_policy, activity.group_key,
           activity.dedupe_key, activity.created_at,
           activity.entity_id,
           actor.id AS actor_id, actor_profile.nickname AS actor_nickname,
           actor_profile.avatar AS actor_avatar,
           target.id AS target_id, target_profile.nickname AS target_nickname,
           target_profile.avatar AS target_avatar,
           entry.id AS entry_id, entry.status AS entry_status,
           entry.simple_rating AS entry_simple_rating,
           entry.rating AS entry_rating, entry.comment AS entry_comment,
           entry.watch_start_date AS entry_watch_start,
           entry.watch_end_date AS entry_watch_end,
           entry.is_public AS entry_is_public,
           entry.entity_id AS entry_entity_id,
           review.id AS review_id, review.title AS review_title,
           review.content AS review_content, review.is_public AS review_is_public,
           review.is_spoiler AS review_is_spoiler,
           review.created_at AS review_created_at,
           review_entry.entity_id AS review_entity_id,
           collection.id AS collection_id, collection.name AS collection_name,
           collection.simple_rating AS collection_simple_rating,
           collection.note AS collection_note,
           collection.is_public AS collection_is_public,
           item.id AS item_id, item.order AS item_order,
           item.relation AS item_relation,
           item_entry.entity_id AS item_entity_id,
           post.id AS post_id, post.content AS post_content,
           post.visibility AS post_visibility, post.is_spoiler AS post_is_spoiler,
           post.is_nsfw AS post_is_nsfw, post.created_at AS post_created_at,
           post.entity_id AS post_entity_id,
           comment.id AS comment_id, comment.content AS comment_content,
           comment.visibility AS comment_visibility,
           comment.is_spoiler AS comment_is_spoiler,
           comment.created_at AS comment_created_at,
           (SELECT count(*) FROM community_reaction AS reaction
             WHERE reaction.activity_id = activity.id
               AND reaction.reaction_type = 'like') AS reaction_count,
           EXISTS (SELECT 1 FROM community_reaction AS reaction
                    WHERE reaction.activity_id = activity.id
                      AND reaction.reaction_type = 'like'
                      AND reaction.user_id = :viewer) AS viewer_has_liked
    FROM community_activity AS activity
    LEFT JOIN "user" AS actor ON actor.id = activity.user_id
    LEFT JOIN user_profile AS actor_profile ON actor_profile.user_id = actor.id
    LEFT JOIN "user" AS target ON target.id = activity.target_user_id
    LEFT JOIN user_profile AS target_profile ON target_profile.user_id = target.id
    LEFT JOIN user_library_entry AS entry ON entry.id = activity.user_subject_id
    LEFT JOIN user_review AS review ON review.id = activity.review_id
    LEFT JOIN user_library_entry AS review_entry
      ON review_entry.id = review.user_subject_id
    LEFT JOIN user_collection AS collection ON collection.id = activity.collection_id
    LEFT JOIN user_collection_item AS item ON item.id = activity.collection_item_id
    LEFT JOIN user_collection AS item_collection
      ON item_collection.id = item.collection_id
    LEFT JOIN user_library_entry AS item_entry
      ON item_entry.id = item.user_subject_id
    LEFT JOIN community_post AS post ON post.id = activity.post_id
    LEFT JOIN community_comment AS comment ON comment.id = activity.comment_id
"""


def _iso(value: Any) -> str | None:
    return isoformat(value) if value is not None else None


async def _entity(session: AsyncSession, row: Any) -> dict[str, Any] | None:
    entity_id = (
        row.entity_id
        or row.entry_entity_id
        or row.item_entity_id
        or row.review_entity_id
        or row.post_entity_id
    )
    if entity_id is None:
        return None
    root = await resolve(session, entity_id) or entity_id
    cluster = await cluster_ids(session, root)
    return await entity_summary(
        session, root=root, cluster_ids=[str(value) for value in cluster], language=""
    )


async def activity_payload(session: AsyncSession, row: Any) -> dict[str, Any]:
    entry = None
    if row.entry_id is not None:
        entry = {
            "id": row.entry_id,
            "status": row.entry_status,
            "simple_rating": row.entry_simple_rating,
            "rating": float(row.entry_rating) if row.entry_rating is not None else None,
            "comment": row.entry_comment,
            "watch_start_date": _iso(row.entry_watch_start),
            "watch_end_date": _iso(row.entry_watch_end),
            "is_public": row.entry_is_public,
        }
    review = (
        {
            "id": row.review_id,
            "title": row.review_title,
            "content": row.review_content,
            "is_public": row.review_is_public,
            "is_spoiler": row.review_is_spoiler,
            "created_at": _iso(row.review_created_at),
        }
        if row.review_id is not None
        else None
    )
    collection = (
        {
            "id": row.collection_id,
            "name": row.collection_name,
            "simple_rating": row.collection_simple_rating,
            "note": row.collection_note,
            "is_public": row.collection_is_public,
        }
        if row.collection_id is not None
        else None
    )
    item = (
        {
            "id": row.item_id,
            "order": row.item_order,
            "relation": row.item_relation,
        }
        if row.item_id is not None
        else None
    )
    post = (
        {
            "id": row.post_id,
            "content": row.post_content,
            "visibility": row.post_visibility,
            "is_spoiler": row.post_is_spoiler,
            "is_nsfw": row.post_is_nsfw,
            "created_at": _iso(row.post_created_at),
        }
        if row.post_id is not None
        else None
    )
    comment = (
        {
            "id": row.comment_id,
            "content": row.comment_content,
            "visibility": row.comment_visibility,
            "is_spoiler": row.comment_is_spoiler,
            "created_at": _iso(row.comment_created_at),
        }
        if row.comment_id is not None
        else None
    )
    return {
        "id": row.id,
        "activity_type": row.activity_type,
        "user": person(row.actor_id, row.actor_nickname, row.actor_avatar),
        "target_user": person(row.target_id, row.target_nickname, row.target_avatar),
        "library_entry": entry,
        "entity": await _entity(session, row),
        "review": review,
        "collection": collection,
        "collection_item": item,
        "post": post,
        "comment": comment,
        "message": row.message,
        "visibility": row.visibility,
        "feed_policy": row.feed_policy,
        "reaction_count": int(row.reaction_count),
        "viewer_state": {"has_liked": bool(row.viewer_has_liked)},
        "group_key": row.group_key,
        "dedupe_key": row.dedupe_key,
        "created_at": _iso(row.created_at),
    }


PUBLIC = """
    activity.visibility = 'public' AND activity.feed_policy <> 'hidden'
    AND (activity.user_subject_id IS NULL OR entry.is_public)
    AND (activity.review_id IS NULL OR (review.is_public AND review_entry.is_public))
    AND (activity.collection_id IS NULL OR collection.is_public)
    AND (activity.collection_item_id IS NULL
         OR (item_collection.is_public AND item_entry.is_public))
    AND activity.user_id NOT IN (
        SELECT blocked_user_id FROM community_user_block WHERE user_id = :viewer)
    AND activity.user_id NOT IN (
        SELECT user_id FROM community_user_block WHERE blocked_user_id = :viewer)
    AND activity.user_id NOT IN (
        SELECT muted_user_id FROM community_user_mute WHERE user_id = :viewer)
"""


async def list_activities(
    session: AsyncSession,
    *,
    viewer_id: int,
    owner_id: int | None,
    cursor: Cursor,
    page_size: int,
    public_only: bool = False,
    feed: bool = False,
    include_self: bool = False,
) -> tuple[list[dict[str, Any]], Cursor | None]:
    clauses = []
    params: dict[str, Any] = {
        "viewer": viewer_id,
        "limit": page_size + 1,
        "offset": cursor.offset,
    }
    if owner_id is not None:
        clauses.append("activity.user_id = :owner")
        params["owner"] = owner_id
    if public_only:
        clauses.append(PUBLIC)
    if feed:
        following = "SELECT following_id FROM community_user_follow WHERE follower_id = :viewer"
        if include_self:
            clauses.append(f"(activity.user_id IN ({following}) OR activity.user_id = :viewer)")
        else:
            clauses.append(f"activity.user_id IN ({following})")
    if cursor.position is not None:
        clauses.append("activity.created_at < CAST(:position AS timestamptz)")
        params["position"] = cursor.position
    rows = await fetch(
        session,
        ACTIVITY_QUERY
        + " WHERE "
        + " AND ".join(clauses)
        + " ORDER BY activity.created_at DESC, activity.id DESC"
        " LIMIT :limit OFFSET :offset",
        params,
    )
    page = rows[:page_size]
    extra = rows[page_size] if len(rows) > page_size else None
    next_cursor = (
        Cursor(offset=0, reverse=False, position=position_of(page[-1]))
        if extra is not None and page
        else None
    )
    return [await activity_payload(session, row) for row in page], next_cursor
