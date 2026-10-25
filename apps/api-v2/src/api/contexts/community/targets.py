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
