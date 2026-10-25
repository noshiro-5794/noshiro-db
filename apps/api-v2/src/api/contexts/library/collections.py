"""A user's public collections."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

ORDERINGS = {
    "id": "collection.id",
    "-id": "collection.id DESC",
    "name": "collection.name",
    "-name": "collection.name DESC",
    "simple_rating": "collection.simple_rating",
    "-simple_rating": "collection.simple_rating DESC",
    "item_count": "item_count",
    "-item_count": "item_count DESC",
}


async def list_public_collections(
    session: AsyncSession,
    *,
    viewer_id: int,
    user_id: int,
    keyword: str,
    ordering: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    order = ORDERINGS.get(ordering, "collection.id")
    clauses = ["collection.user_id = :user_id", "collection.is_public"]
    params: dict[str, Any] = {"user_id": user_id, "viewer": viewer_id}
    if keyword:
        clauses.append("collection.name ILIKE :keyword")
        params["keyword"] = f"%{keyword}%"
    clause = " AND ".join(clauses)
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM user_collection AS collection WHERE {clause}",
        params,
    )
    rows = await fetch(
        session,
        """
        SELECT collection.id, collection.name, collection.simple_rating,
               collection.note, collection.is_public,
               (SELECT count(*) FROM user_collection_item AS item
                 WHERE item.collection_id = collection.id) AS item_count,
               (SELECT count(*) FROM community_reaction AS reaction
                 WHERE reaction.collection_id = collection.id
                   AND reaction.reaction_type = 'like') AS reaction_count,
               EXISTS (SELECT 1 FROM community_reaction AS reaction
                        WHERE reaction.collection_id = collection.id
                          AND reaction.reaction_type = 'like'
                          AND reaction.user_id = :viewer) AS has_liked,
               EXISTS (SELECT 1 FROM community_bookmark AS bookmark
                        WHERE bookmark.collection_id = collection.id
                          AND bookmark.user_id = :viewer) AS has_bookmarked
        FROM user_collection AS collection
        """
        + f" WHERE {clause} ORDER BY {order} LIMIT :limit OFFSET :offset",
        {
            **params,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    return int(total[0].total), [
        {
            "id": row.id,
            "name": row.name,
            "simple_rating": row.simple_rating,
            "note": row.note,
            "is_public": row.is_public,
            "item_count": int(row.item_count),
            "reaction_count": int(row.reaction_count),
            "viewer_state": {
                "has_liked": bool(row.has_liked),
                "has_bookmarked": bool(row.has_bookmarked),
            },
        }
        for row in rows
    ]
