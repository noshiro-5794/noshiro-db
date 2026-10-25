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
    public_only: bool = True,
) -> tuple[int, list[dict[str, Any]]]:
    order = ORDERINGS.get(ordering, "collection.id")
    clauses = ["collection.user_id = :user_id"]
    if public_only:
        clauses.append("collection.is_public")
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


BLANK_NAME = "UserCollection name can not be blank."


async def create_collection(
    session: AsyncSession, *, user_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    errors: dict[str, list[str]] = {}
    name = body.get("name")
    if not isinstance(name, str):
        errors["name"] = ["This field is required."]
    elif not name.strip():
        errors["name"] = [BLANK_NAME]
    elif len(name) > 256:
        errors["name"] = ["Ensure this field has no more than 256 characters."]
    rating = body.get("simple_rating")
    if rating is not None and (
        not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5
    ):
        errors["simple_rating"] = ["Ensure this value is between 1 and 5."]
    note = body.get("note", "")
    if not isinstance(note, str):
        errors["note"] = ["Not a valid string."]
    elif len(note) > 5000:
        errors["note"] = ["Ensure this field has no more than 5000 characters."]
    if errors:
        raise ValueError(errors)
    rows = await fetch(
        session,
        "INSERT INTO user_collection (name, simple_rating, note, is_public, user_id)"
        " VALUES (:name, :rating, :note, :public, :user_id) RETURNING id",
        {
            "name": name.strip(),
            "rating": rating,
            "note": note,
            "public": bool(body.get("is_public", True)),
            "user_id": user_id,
        },
    )
    await session.commit()
    return await collection_by_id(session, viewer_id=user_id, collection_id=rows[0].id)


async def collection_by_id(
    session: AsyncSession, *, viewer_id: int, collection_id: int
) -> dict[str, Any]:
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
        FROM user_collection AS collection WHERE collection.id = :id
        """,
        {"id": collection_id, "viewer": viewer_id},
    )
    if not rows:
        raise LookupError(collection_id)
    row = rows[0]
    return {
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
