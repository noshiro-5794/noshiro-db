"""The summary every payload gives for the thing it points at.

A notification, a comment and a report all name a target by type and id, and the
shape depends on the type. This module is where those shapes live so the payload
builders stay about their own fields.
"""

from __future__ import annotations

from typing import Any

from api.contexts.community.people import person

ACTIVITY = "activity"


def activity_target(row: Any) -> dict[str, Any] | None:
    """A timeline entry: who did it and, when it concerns someone, who."""
    if row.activity_id is None:
        return None
    return {
        "type": ACTIVITY,
        "id": row.activity_id,
        "user": person(
            row.activity_user_id,
            row.activity_user_nickname,
            row.activity_user_avatar,
        ),
        "target_user": person(
            row.activity_target_id,
            row.activity_target_nickname,
            row.activity_target_avatar,
        ),
    }


def _base(kind: str, target_id: Any) -> dict[str, Any] | None:
    if target_id is None:
        return None
    return {"type": kind, "id": target_id}


def post_target(row: Any) -> dict[str, Any] | None:
    """A post names its author; the body is fetched when the caller needs it."""
    target = _base("post", row.post_id)
    if target is None:
        return None
    target["author"] = person(row.post_author_id, row.post_nickname, row.post_avatar)
    return target


def comment_target(row: Any) -> dict[str, Any] | None:
    target = _base("comment", row.comment_id)
    if target is None:
        return None
    target["author"] = person(row.comment_author_id, row.comment_nickname, row.comment_avatar)
    return target


def review_target(row: Any) -> dict[str, Any] | None:
    target = _base("review", row.review_id)
    if target is None:
        return None
    target["author"] = person(row.review_author_id, row.review_nickname, row.review_avatar)
    return target


def collection_target(row: Any) -> dict[str, Any] | None:
    target = _base("collection", row.collection_id)
    if target is None:
        return None
    target["owner"] = person(
        row.collection_owner_id, row.collection_nickname, row.collection_avatar
    )
    return target


def first_target(row: Any) -> dict[str, Any] | None:
    """The report and notification payloads name whichever target is set."""
    for resolve in (post_target, comment_target, review_target, collection_target):
        target = resolve(row)
        if target is not None:
            return target
    return activity_target(row)


def post_summary(row: Any, entity: dict[str, Any] | None) -> dict[str, Any] | None:
    if row.post_id is None:
        return None
    first = (row.post_content or "").splitlines()
    return {
        "type": "post",
        "id": row.post_id,
        "title": first[0][:96] if first else "",
        "entity": entity,
        "author": person(row.author_id, row.author_nickname, row.author_avatar),
        "created_at": row.post_created_at,
    }


def review_summary(row: Any, entity: dict[str, Any] | None) -> dict[str, Any] | None:
    if row.review_id is None:
        return None
    return {
        "type": "review",
        "id": row.review_id,
        "title": row.review_title,
        "body": (row.review_content or "")[:240],
        "entity": entity,
        "author": person(row.author_id, row.author_nickname, row.author_avatar),
        "is_spoiler": row.review_is_spoiler,
        "created_at": row.review_created_at,
    }


def collection_summary(row: Any) -> dict[str, Any] | None:
    if row.collection_id is None:
        return None
    return {
        "type": "collection",
        "id": row.collection_id,
        "title": row.collection_name,
        "body": (row.collection_note or "")[:240],
        "author": person(row.author_id, row.author_nickname, row.author_avatar),
        "simple_rating": row.collection_simple_rating,
    }
