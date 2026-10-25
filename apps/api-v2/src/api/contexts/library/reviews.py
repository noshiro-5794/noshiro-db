"""The reviews attached to one library entry.

The reaction and bookmark tables keep one foreign key per target type, so the
counts join on `review_id` rather than filtering a polymorphic pair.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.community.activities import create_review_activity
from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.fragments import fetch, isoformat
from api.contexts.presentation.summary import entity_summary

REVIEW_QUERY = """
    SELECT review.id, review.title, review.content, review.is_public,
           review.is_spoiler, review.created_at, review.updated_at,
           review.user_subject_id, entry.user_id AS author_id, entry.entity_id,
           profile.nickname, profile.avatar,
           (SELECT count(*) FROM community_reaction AS reaction
             WHERE reaction.review_id = review.id
               AND reaction.reaction_type = 'like') AS reaction_count,
           EXISTS (SELECT 1 FROM community_reaction AS reaction
                    WHERE reaction.review_id = review.id
                      AND reaction.reaction_type = 'like'
                      AND reaction.user_id = :viewer) AS has_liked,
           EXISTS (SELECT 1 FROM community_bookmark AS bookmark
                    WHERE bookmark.review_id = review.id
                      AND bookmark.user_id = :viewer) AS has_bookmarked
    FROM user_review AS review
    JOIN user_library_entry AS entry ON entry.id = review.user_subject_id
    LEFT JOIN user_profile AS profile ON profile.user_id = entry.user_id
"""


async def review_data(session: AsyncSession, row: Any) -> dict[str, Any]:
    root = await resolve(session, row.entity_id) or row.entity_id
    cluster = await cluster_ids(session, root)
    summary = await entity_summary(
        session,
        root=root,
        cluster_ids=[str(value) for value in cluster],
        language="",
    )
    return {
        "id": row.id,
        "title": row.title,
        "content": row.content,
        "is_public": row.is_public,
        "is_spoiler": row.is_spoiler,
        "created_at": isoformat(row.created_at),
        "updated_at": isoformat(row.updated_at),
        "reaction_count": int(row.reaction_count),
        "entity": summary,
        "library_entry_id": row.user_subject_id,
        "user": {
            "id": row.author_id,
            "nickname": row.nickname or "",
            "avatar": row.avatar or "",
        },
        "viewer_state": {
            "has_liked": bool(row.has_liked),
            "has_bookmarked": bool(row.has_bookmarked),
        },
    }


async def entry_reviews(
    session: AsyncSession, *, user_id: int, entry_id: int
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        REVIEW_QUERY + " WHERE review.user_subject_id = :entry_id AND entry.user_id = :user_id"
        " AND entry.entity_id IS NOT NULL"
        " ORDER BY review.created_at DESC, review.id DESC",
        {"entry_id": entry_id, "user_id": user_id, "viewer": user_id},
    )
    return [await review_data(session, row) for row in rows]


BLANK_TITLE = "UserReview title can not be blank."


async def create_review(
    session: AsyncSession, *, user_id: int, entry_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    raw_title = body.get("title")
    raw_content = body.get("content")
    title = raw_title if isinstance(raw_title, str) else ""
    content = raw_content if isinstance(raw_content, str) else ""
    errors: dict[str, list[str]] = {}
    if not title:
        errors["title"] = ["This field is required."]
    elif not title.strip():
        errors["title"] = [BLANK_TITLE]
    elif len(title) > 256:
        errors["title"] = ["Ensure this field has no more than 256 characters."]
    if not content:
        errors["content"] = ["This field is required."]
    elif len(content) > 20000:
        errors["content"] = ["Ensure this field has no more than 20000 characters."]
    if errors:
        raise ValueError(errors)
    entry = await fetch(
        session,
        "SELECT id, entity_id, is_public FROM user_library_entry"
        " WHERE id = :entry_id AND user_id = :user_id AND entity_id IS NOT NULL",
        {"entry_id": entry_id, "user_id": user_id},
    )
    if not entry:
        raise LookupError(entry_id)
    is_public = bool(body.get("is_public", True))
    is_spoiler = bool(body.get("is_spoiler", False))
    rows = await fetch(
        session,
        "INSERT INTO user_review (title, content, is_public, is_spoiler,"
        " created_at, updated_at, user_subject_id)"
        " VALUES (:title, :content, :public, :spoiler, now(), now(), :entry_id)"
        " RETURNING id",
        {
            "title": title.strip(),
            "content": content,
            "public": is_public,
            "spoiler": is_spoiler,
            "entry_id": entry_id,
        },
    )
    await create_review_activity(
        session,
        user_id=user_id,
        entry_id=entry_id,
        review_id=rows[0].id,
        title=title.strip(),
        entry_is_public=bool(entry[0].is_public),
        review_is_public=is_public,
        entity_id=str(entry[0].entity_id),
    )
    await session.commit()
    found = await fetch(
        session, REVIEW_QUERY + " WHERE review.id = :id", {"id": rows[0].id, "viewer": user_id}
    )
    return await review_data(session, found[0])
