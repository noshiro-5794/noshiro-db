"""The targets a user saved, each rendered the way its own type reads.

One query joins the three branches a bookmark can point at; the payload builder
decides which one the row carries.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.resolution import cluster_ids, resolve
from api.contexts.presentation.fragments import fetch, isoformat
from api.contexts.presentation.summary import entity_summary

from .targets import collection_summary, post_summary, review_summary

QUERY = """
    SELECT bookmark.id, bookmark.created_at,
           bookmark.post_id, bookmark.review_id, bookmark.collection_id,
           post.content AS post_content, post.created_at AS post_created_at,
           post.entity_id AS post_entity_id,
           post_author.id AS author_id,
           post_author_profile.nickname AS author_nickname,
           post_author_profile.avatar AS author_avatar,
           review.title AS review_title, review.content AS review_content,
           review.is_spoiler AS review_is_spoiler,
           review.created_at AS review_created_at,
           review_entry.entity_id AS review_entity_id,
           review_author.id AS review_author_id,
           review_author_profile.nickname AS review_author_nickname,
           review_author_profile.avatar AS review_author_avatar,
           collection.name AS collection_name, collection.note AS collection_note,
           collection.simple_rating AS collection_simple_rating,
           collection_owner.id AS collection_owner_id,
           collection_owner_profile.nickname AS collection_owner_nickname,
           collection_owner_profile.avatar AS collection_owner_avatar
    FROM community_bookmark AS bookmark
    LEFT JOIN community_post AS post ON post.id = bookmark.post_id
    LEFT JOIN "user" AS post_author ON post_author.id = post.author_id
    LEFT JOIN user_profile AS post_author_profile
      ON post_author_profile.user_id = post_author.id
    LEFT JOIN user_review AS review ON review.id = bookmark.review_id
    LEFT JOIN user_library_entry AS review_entry
      ON review_entry.id = review.user_subject_id
    LEFT JOIN "user" AS review_author ON review_author.id = review_entry.user_id
    LEFT JOIN user_profile AS review_author_profile
      ON review_author_profile.user_id = review_author.id
    LEFT JOIN user_collection AS collection
      ON collection.id = bookmark.collection_id
    LEFT JOIN "user" AS collection_owner
      ON collection_owner.id = collection.user_id
    LEFT JOIN user_profile AS collection_owner_profile
      ON collection_owner_profile.user_id = collection_owner.id
"""


def _kind(row: Any) -> str:
    if row.post_id is not None:
        return "post"
    if row.review_id is not None:
        return "review"
    return "collection"


def _target_id(row: Any, kind: str) -> int:
    return int(getattr(row, f"{kind}_id"))


async def _entity(session: AsyncSession, entity_id: Any) -> dict[str, Any] | None:
    if entity_id is None:
        return None
    root = await resolve(session, entity_id) or entity_id
    cluster = await cluster_ids(session, root)
    return await entity_summary(
        session, root=root, cluster_ids=[str(value) for value in cluster], language=""
    )


async def list_bookmarks(
    session: AsyncSession,
    *,
    user_id: int,
    target_type: str,
    keyword: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    where = ["bookmark.user_id = :user_id"]
    params: dict[str, Any] = {}
    if target_type:
        where.append(f"bookmark.{target_type}_id IS NOT NULL")
    if keyword:
        where.append(
            "(post.content ILIKE :keyword OR review.title ILIKE :keyword"
            " OR collection.name ILIKE :keyword)"
        )
        params["keyword"] = f"%{keyword}%"
    clause = " AND ".join(where)
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM community_bookmark AS bookmark"
        f" LEFT JOIN community_post AS post ON post.id = bookmark.post_id"
        f" LEFT JOIN user_review AS review ON review.id = bookmark.review_id"
        f" LEFT JOIN user_collection AS collection"
        f" ON collection.id = bookmark.collection_id WHERE {clause}",
        {**params, "user_id": user_id},
    )
    rows = await fetch(
        session,
        QUERY + f" WHERE {clause}" + " ORDER BY bookmark.created_at DESC, bookmark.id DESC"
        " LIMIT :limit OFFSET :offset",
        {
            **params,
            "user_id": user_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    results = []
    for row in rows:
        kind = _kind(row)
        if kind == "post":
            target = post_summary(row, await _entity(session, row.post_entity_id))
        elif kind == "review":
            target = review_summary(row, await _entity(session, row.review_entity_id))
        else:
            # The collection branch reuses the author fields under its own names.
            target = collection_summary(_CollectionRow(row))
        results.append(
            {
                "id": row.id,
                "target_type": kind,
                "target_id": _target_id(row, kind),
                "target": target,
                "created_at": isoformat(row.created_at),
            }
        )
    return int(total[0].total), results


class _CollectionRow:
    """Maps the collection columns onto the names the summary expects."""

    def __init__(self, row: Any) -> None:
        self.collection_id = row.collection_id
        self.collection_name = row.collection_name
        self.collection_note = row.collection_note
        self.collection_simple_rating = row.collection_simple_rating
        self.author_id = row.collection_owner_id
        self.author_nickname = row.collection_owner_nickname
        self.author_avatar = row.collection_owner_avatar
