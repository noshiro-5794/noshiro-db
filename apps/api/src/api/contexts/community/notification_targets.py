"""Batch-load the nested references carried by notification targets."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.community.people import person
from api.contexts.presentation.fragments import fetch

TARGET_FIELDS = ("activity", "post", "comment", "review", "collection")
USER_FIELDS = "u.id AS user_id,p.nickname,p.avatar"
USER_JOIN = ' LEFT JOIN "user" u ON u.id=item.{owner} LEFT JOIN user_profile p ON p.user_id=u.id '
QUERIES = {
    "post": "SELECT item.id,"
    + USER_FIELDS
    + " FROM community_post item"
    + USER_JOIN.format(owner="author_id"),
    "collection": "SELECT item.id,"
    + USER_FIELDS
    + " FROM user_collection item"
    + USER_JOIN.format(owner="user_id"),
    "review": "SELECT item.id," + USER_FIELDS + " FROM user_review item "
    "LEFT JOIN user_library_entry entry ON entry.id=item.user_subject_id "
    'LEFT JOIN "user" u ON u.id=entry.user_id LEFT JOIN user_profile p ON p.user_id=u.id ',
    "activity": "SELECT item.id,item.post_id,item.comment_id,item.review_id,item.collection_id,"
    "item.entity_id," + USER_FIELDS + ",target.id AS target_user_id,"
    "tp.nickname AS target_nickname,tp.avatar AS target_avatar FROM community_activity item"
    + USER_JOIN.format(owner="user_id")
    + ' LEFT JOIN "user" target ON target.id=item.target_user_id '
    "LEFT JOIN user_profile tp ON tp.user_id=target.id ",
    "comment": "SELECT item.id,item.parent_id,item.post_id,item.review_id,item.collection_id,"
    "item.activity_id,"
    + USER_FIELDS
    + " FROM community_comment item"
    + USER_JOIN.format(owner="author_id"),
}


async def load(session: AsyncSession, notifications: list[Any]) -> dict[int, dict[str, Any] | None]:
    pending: dict[str, set[int]] = {kind: set() for kind in TARGET_FIELDS}
    for notification in notifications:
        for kind in TARGET_FIELDS:
            identifier = getattr(notification, f"{kind}_id")
            if identifier is not None:
                pending[kind].add(identifier)
    cache: dict[tuple[str, int], Any] = {}
    while any(pending.values()):
        current = pending
        pending = {kind: set() for kind in TARGET_FIELDS}
        for kind, identifiers in current.items():
            missing = identifiers - {identifier for target, identifier in cache if target == kind}
            if not missing:
                continue
            rows = await fetch(
                session, QUERIES[kind] + " WHERE item.id=ANY(:ids)", {"ids": list(missing)}
            )
            for identifier in missing:
                cache[kind, identifier] = None
            for row in rows:
                cache[kind, row.id] = row
                if kind in {"activity", "comment"}:
                    for child in TARGET_FIELDS:
                        identifier = getattr(row, f"{child}_id", None)
                        if identifier is not None and (child, identifier) not in cache:
                            pending[child].add(identifier)

    def render(
        kind: str, identifier: int, ancestors: frozenset[tuple[str, int]]
    ) -> dict[str, Any] | None:
        key = kind, identifier
        row = cache.get(key)
        if row is None:
            return None
        result: dict[str, Any] = {"type": kind, "id": identifier}
        if key in ancestors:
            return result
        ancestors = ancestors | {key}
        owner = person(row.user_id, row.nickname, row.avatar)
        if kind == "activity":
            result["user"] = owner
            result["target_user"] = person(
                row.target_user_id, row.target_nickname, row.target_avatar
            )
            if row.entity_id is not None:
                result["entity"] = {"id": str(row.entity_id)}
        else:
            result["owner" if kind == "collection" else "author"] = owner
        if kind == "comment":
            result["parent_id"] = row.parent_id
        if kind in {"activity", "comment"}:
            for child in TARGET_FIELDS:
                child_id = getattr(row, f"{child}_id", None)
                if child_id is not None:
                    result[child] = render(child, child_id, ancestors)
        return result

    results = {}
    for notification in notifications:
        target = None
        for kind in TARGET_FIELDS:
            identifier = getattr(notification, f"{kind}_id")
            if identifier is not None:
                target = render(kind, identifier, frozenset())
                break
        results[notification.id] = target
    return results
