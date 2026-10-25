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
    raw_name = body.get("name")
    name = raw_name if isinstance(raw_name, str) else ""
    if not name:
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


async def my_collection(
    session: AsyncSession, *, user_id: int, collection_id: int
) -> dict[str, Any]:
    rows = await fetch(
        session,
        "SELECT user_id FROM user_collection WHERE id = :id",
        {"id": collection_id},
    )
    if not rows or rows[0].user_id != user_id:
        raise LookupError(collection_id)
    return await collection_by_id(session, viewer_id=user_id, collection_id=collection_id)


async def update_collection(
    session: AsyncSession, *, user_id: int, collection_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    await my_collection(session, user_id=user_id, collection_id=collection_id)
    errors: dict[str, list[str]] = {}
    sets: list[str] = []
    params: dict[str, Any] = {"id": collection_id}
    if "name" in body:
        raw_name = body["name"]
        name = raw_name if isinstance(raw_name, str) else ""
        if not name.strip():
            errors["name"] = [BLANK_NAME]
        elif len(name) > 256:
            errors["name"] = ["Ensure this field has no more than 256 characters."]
        else:
            sets.append("name = :name")
            params["name"] = name.strip()
    if "simple_rating" in body:
        rating = body["simple_rating"]
        if rating is not None and (
            not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5
        ):
            errors["simple_rating"] = ["Ensure this value is between 1 and 5."]
        else:
            sets.append("simple_rating = :rating")
            params["rating"] = rating
    if "note" in body:
        note = body["note"]
        if not isinstance(note, str):
            errors["note"] = ["Not a valid string."]
        elif len(note) > 5000:
            errors["note"] = ["Ensure this field has no more than 5000 characters."]
        else:
            sets.append("note = :note")
            params["note"] = note
    if "is_public" in body:
        sets.append("is_public = :public")
        params["public"] = bool(body["is_public"])
    if errors:
        raise ValueError(errors)
    if sets:
        await fetch(
            session,
            "UPDATE user_collection SET " + ", ".join(sets) + " WHERE id = :id RETURNING id",
            params,
        )
        await session.commit()
    return await collection_by_id(session, viewer_id=user_id, collection_id=collection_id)


async def delete_collection(session: AsyncSession, *, user_id: int, collection_id: int) -> None:
    await my_collection(session, user_id=user_id, collection_id=collection_id)
    await fetch(
        session,
        "DELETE FROM community_activity WHERE collection_id = :id RETURNING id",
        {"id": collection_id},
    )
    await fetch(
        session,
        "DELETE FROM user_collection_item WHERE collection_id = :id RETURNING id",
        {"id": collection_id},
    )
    await fetch(
        session,
        "DELETE FROM user_collection WHERE id = :id RETURNING id",
        {"id": collection_id},
    )
    await session.commit()


async def list_items(
    session: AsyncSession,
    *,
    viewer_id: int,
    user_id: int,
    collection_id: int,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    await my_collection(session, user_id=user_id, collection_id=collection_id)
    total = await fetch(
        session,
        "SELECT count(*) AS total FROM user_collection_item WHERE collection_id = :id",
        {"id": collection_id},
    )
    rows = await fetch(
        session,
        """
        SELECT item.id, item.user_subject_id, item.order, item.relation,
               entry.entity_id
        FROM user_collection_item AS item
        JOIN user_library_entry AS entry ON entry.id = item.user_subject_id
        WHERE item.collection_id = :id
        ORDER BY item.order ASC, item.id ASC
        LIMIT :limit OFFSET :offset
        """,
        {
            "id": collection_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    return int(total[0].total), [
        {
            "id": row.id,
            "library_entry_id": row.user_subject_id,
            "entity": await entity_for(session, row.entity_id),
            "order": row.order,
            "relation": row.relation,
        }
        for row in rows
    ]


async def entity_for(session: AsyncSession, entity_id: Any) -> dict[str, Any] | None:
    from api.contexts.identity.resolution import cluster_ids, resolve
    from api.contexts.presentation.summary import entity_summary

    if entity_id is None:
        return None
    root = await resolve(session, entity_id) or entity_id
    cluster = await cluster_ids(session, root)
    return await entity_summary(
        session, root=root, cluster_ids=[str(value) for value in cluster], language=""
    )


async def add_item(
    session: AsyncSession,
    *,
    user_id: int,
    collection_id: int,
    body: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    await my_collection(session, user_id=user_id, collection_id=collection_id)
    entry_id = body.get("library_entry_id")
    if not isinstance(entry_id, int) or isinstance(entry_id, bool) or entry_id < 1:
        raise ValueError({"library_entry_id": ["A valid integer is required."]})
    entry = await fetch(
        session,
        "SELECT entity_id FROM user_library_entry WHERE id = :id AND user_id = :user_id",
        {"id": entry_id, "user_id": user_id},
    )
    if not entry:
        raise LookupError(entry_id)
    existing = await fetch(
        session,
        "SELECT id FROM user_collection_item"
        " WHERE collection_id = :collection AND user_subject_id = :entry",
        {"collection": collection_id, "entry": entry_id},
    )
    if existing:
        rows = await fetch(
            session,
            'SELECT id, user_subject_id, "order", relation FROM user_collection_item'
            " WHERE id = :id",
            {"id": existing[0].id},
        )
        row = rows[0]
        return (
            {
                "id": row.id,
                "library_entry_id": row.user_subject_id,
                "entity": await entity_for(session, entry[0].entity_id),
                "order": row.order,
                "relation": row.relation,
            },
            False,
        )
    created = await fetch(
        session,
        'INSERT INTO user_collection_item ("order", relation, collection_id,'
        " user_subject_id) VALUES (:order, :relation, :collection, :entry)"
        " RETURNING id",
        {
            "order": body.get("order", 0),
            "relation": body.get("relation", "") or "",
            "collection": collection_id,
            "entry": entry_id,
        },
    )
    await session.commit()
    return (
        {
            "id": created[0].id,
            "library_entry_id": entry_id,
            "entity": await entity_for(session, entry[0].entity_id),
            "order": body.get("order", 0),
            "relation": body.get("relation", "") or "",
        },
        True,
    )
