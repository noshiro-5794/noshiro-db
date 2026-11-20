"""Comments, reply counts, activities and notifications for public targets."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch, isoformat
from api.shared.pagination import page_offset

from .errors import CommentPermissionDenied, InteractionBlocked
from .people import person
from .visibility import visible

QUERY = """
    SELECT comment.id, comment.parent_id, comment.content, comment.visibility,
           comment.is_spoiler, comment.is_hidden, comment.is_locked,
           comment.reply_count, comment.reaction_count,
           comment.created_at, comment.updated_at,
           comment.post_id, comment.review_id, comment.collection_id, comment.activity_id,
           author.id AS author_id, author_profile.nickname AS author_nickname,
           author_profile.avatar AS author_avatar,
           EXISTS (SELECT 1 FROM community_reaction AS reaction
                    WHERE reaction.comment_id = comment.id
                      AND reaction.reaction_type = 'like'
                      AND reaction.user_id = :viewer) AS has_liked,
           EXISTS (SELECT 1 FROM community_user_follow AS follow
                    WHERE follow.follower_id = :viewer
                      AND follow.following_id = comment.author_id)
             AS is_following_author
    FROM community_comment AS comment
    JOIN "user" AS author ON author.id = comment.author_id
    LEFT JOIN user_profile AS author_profile ON author_profile.user_id = author.id
"""

TARGETS = ("post", "review", "collection", "activity")
TARGET_TABLES = {
    "post": "community_post",
    "review": "user_review",
    "collection": "user_collection",
    "activity": "community_activity",
}
TARGET_QUERIES = {
    "post": "SELECT target.id,target.author_id AS owner_id,target.entity_id,target.is_locked"
    " FROM community_post AS target WHERE target.id=:id",
    "review": "SELECT target.id,entry.user_id AS owner_id,entry.entity_id,false AS is_locked"
    " FROM user_review AS target JOIN user_library_entry AS entry"
    " ON entry.id=target.user_subject_id"
    " WHERE target.id=:id",
    "collection": "SELECT target.id,target.user_id AS owner_id,NULL::uuid AS entity_id,"
    " false AS is_locked FROM user_collection AS target WHERE target.id=:id",
    "activity": "SELECT target.id,target.user_id AS owner_id,target.entity_id,false AS is_locked"
    " FROM community_activity AS target WHERE target.id=:id",
}


async def _blocked(session: AsyncSession, actor: int, owner: int) -> bool:
    return bool(
        await fetch(
            session,
            "SELECT 1 FROM community_user_block WHERE (user_id=:actor AND blocked_user_id=:owner)"
            " OR (user_id=:owner AND blocked_user_id=:actor)",
            {"actor": actor, "owner": owner},
        )
    )


async def _comment_target(
    session: AsyncSession, kind: str, identifier: int, *, actor: int | None = None
) -> Any:
    if kind not in TARGETS:
        raise ValueError({"target_type": [f'"{kind}" is not a valid choice.']})
    rows = await fetch(
        session,
        TARGET_QUERIES[kind] + (" FOR UPDATE OF target" if actor is not None else ""),
        {"id": identifier},
    )
    if not rows or not await visible(session, kind, identifier):
        raise FileNotFoundError(identifier)
    target = rows[0]
    if actor is not None and await _blocked(session, actor, target.owner_id):
        raise InteractionBlocked(identifier)
    return target


def _target(row: Any) -> dict[str, Any] | None:
    for kind in TARGETS:
        target_id = getattr(row, f"{kind}_id", None)
        if target_id is not None:
            return {"type": kind, "id": target_id}
    return None


async def comment_payload(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "parent_id": row.parent_id,
        "target": _target(row),
        "content": row.content,
        "visibility": row.visibility,
        "is_spoiler": row.is_spoiler,
        "is_hidden": row.is_hidden,
        "is_locked": row.is_locked,
        "reply_count": row.reply_count,
        "reaction_count": row.reaction_count,
        "created_at": isoformat(row.created_at),
        "updated_at": isoformat(row.updated_at),
        "author": (
            None if row.is_hidden else person(row.author_id, row.author_nickname, row.author_avatar)
        ),
        "viewer_state": {
            "has_liked": bool(row.has_liked),
            "is_following_author": bool(row.is_following_author),
        },
    }


async def list_comments(
    session: AsyncSession,
    *,
    viewer_id: int,
    target_type: str,
    target_id: int,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    await _comment_target(session, target_type, target_id)
    clauses = [
        f"comment.{target_type}_id = :target_id",
        "comment.visibility = 'public'",
        "(comment.is_hidden = false OR comment.reply_count > 0)",
        """comment.author_id NOT IN (
            SELECT blocked_user_id FROM community_user_block WHERE user_id = :viewer)""",
        """comment.author_id NOT IN (
            SELECT user_id FROM community_user_block WHERE blocked_user_id = :viewer)""",
        """comment.author_id NOT IN (
            SELECT muted_user_id FROM community_user_mute WHERE user_id = :viewer)""",
    ]
    params: dict[str, Any] = {"target_id": target_id, "viewer": viewer_id}
    clause = " AND ".join(clauses)
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM community_comment AS comment WHERE {clause}",
        params,
    )
    rows = await fetch(
        session,
        QUERY + f" WHERE {clause}" + " ORDER BY comment.created_at ASC, comment.id ASC"
        " LIMIT :limit OFFSET :offset",
        {
            **params,
            "limit": page_size,
            "offset": page_offset(page, page_size, int(total[0].total)),
        },
    )
    return int(total[0].total), [await comment_payload(row) for row in rows]


VISIBILITIES = ("public", "private", "followers")


async def _comment_row(session: AsyncSession, *, viewer_id: int, comment_id: int) -> Any:
    rows = await fetch(
        session, QUERY + " WHERE comment.id = :id", {"id": comment_id, "viewer": viewer_id}
    )
    if not rows:
        raise LookupError(comment_id)
    return rows[0]


async def create_comment(
    session: AsyncSession,
    *,
    user_id: int,
    target_type: str,
    target_id: int,
    body: dict[str, Any],
) -> dict[str, Any]:
    errors: dict[str, list[str]] = {}
    content = body.get("content")
    if not isinstance(content, str):
        errors["content"] = ["This field is required."]
    elif not content.strip():
        errors["content"] = ["Comment content can not be blank."]
    elif len(content) > 5000:
        errors["content"] = ["Ensure this field has no more than 5000 characters."]
    visibility = body.get("visibility", "public")
    if visibility not in VISIBILITIES:
        errors["visibility"] = [f'"{visibility}" is not a valid choice.']
    if errors:
        raise ValueError(errors)
    target = await _comment_target(session, target_type, target_id, actor=user_id)
    if target.is_locked:
        raise PermissionError(target_id)
    parent_id = body.get("parent_id") or None
    recipient_id = target.owner_id
    if parent_id is not None:
        parent = await fetch(
            session,
            "SELECT id,author_id,is_locked,is_hidden FROM community_comment"
            f" WHERE id=:id AND {target_type}_id=:target FOR UPDATE",
            {"id": parent_id, "target": target_id},
        )
        if not parent:
            raise LookupError(parent_id)
        if parent[0].is_locked or parent[0].is_hidden:
            raise PermissionError(parent_id)
        if await _blocked(session, user_id, parent[0].author_id):
            raise InteractionBlocked(parent_id)
        recipient_id = parent[0].author_id
    created = await fetch(
        session,
        """
        INSERT INTO community_comment (
            content, visibility, is_spoiler, is_hidden, is_locked, reply_count,
            reaction_count, created_at, updated_at, metadata, author_id, parent_id,
        """
        + f" {target_type}_id"
        + """
        ) VALUES (
            :content, :visibility, :spoiler, false, false, 0, 0, now(), now(),
            '{}'::jsonb, :author, :parent,
        """
        + " :target_id"
        + """
        ) RETURNING id
        """,
        {
            "content": content,
            "visibility": visibility,
            "spoiler": bool(body.get("is_spoiler", False)),
            "author": user_id,
            "parent": parent_id,
            "target_id": target_id,
        },
    )
    comment_id = created[0].id
    if target_type == "post":
        await fetch(
            session,
            "UPDATE community_post SET reply_count=reply_count+1,last_activity_at=now()"
            " WHERE id=:id RETURNING id",
            {"id": target_id},
        )
    if parent_id is not None:
        await fetch(
            session,
            "UPDATE community_comment SET reply_count = reply_count + 1"
            " WHERE id = :id RETURNING id",
            {"id": parent_id},
        )
    activity_target = target_type if target_type != "activity" else None
    target_column = f",{activity_target}_id" if activity_target else ""
    target_value = ",:target" if activity_target else ""
    metadata = {"target": {"type": target_type, "id": target_id}, "comment": {"id": comment_id}}
    activities = await fetch(
        session,
        "INSERT INTO community_activity(user_id,entity_id,activity_type,comment_id,message,"
        "visibility,feed_policy,group_key,dedupe_key,metadata,created_at" + target_column + ")"
        " VALUES (:author,:entity,'comment_created',:comment,:message,:visibility,'normal',"
        ":group_key,:dedupe_key,CAST(:metadata AS jsonb),now()" + target_value + ") RETURNING id",
        {
            "author": user_id,
            "entity": target.entity_id,
            "comment": comment_id,
            "message": f"Commented on a {target_type}",
            "visibility": visibility,
            "group_key": f"{target_type}_comment:{target_id}",
            "dedupe_key": f"comment_created:{comment_id}",
            "metadata": json.dumps(metadata),
            "target": target_id,
        },
    )
    if recipient_id != user_id:
        notification_metadata = {
            "post_id": target_id if target_type == "post" else None,
            "comment_id": comment_id,
            "review_id": target_id if target_type == "review" else None,
            "collection_id": target_id if target_type == "collection" else None,
        }
        await fetch(
            session,
            "INSERT INTO community_notification(recipient_id,actor_id,activity_id,comment_id,"
            "notification_type,metadata,created_at" + target_column + ")"
            " VALUES (:recipient,:actor,:activity,:comment,'commented',CAST(:metadata AS jsonb),"
            "now()" + target_value + ") RETURNING id",
            {
                "recipient": recipient_id,
                "actor": user_id,
                "activity": activities[0].id,
                "comment": comment_id,
                "metadata": json.dumps(notification_metadata),
                "target": target_id,
            },
        )
    await session.commit()
    return await comment_payload(
        await _comment_row(session, viewer_id=user_id, comment_id=comment_id)
    )


async def _mine(session: AsyncSession, user_id: int, comment_id: int) -> Any:
    rows = await fetch(
        session,
        "SELECT id,author_id,post_id,review_id,collection_id,activity_id FROM community_comment"
        " WHERE id=:id",
        {"id": comment_id},
    )
    if not rows:
        raise LookupError(comment_id)
    if rows[0].author_id != user_id:
        raise CommentPermissionDenied(comment_id)
    target = _target(rows[0])
    assert target is not None
    # Creation and deletion take the target lock before a comment lock.
    await fetch(
        session,
        f"SELECT id FROM {TARGET_TABLES[target['type']]} WHERE id=:id FOR UPDATE",
        {"id": target["id"]},
    )
    locked = await fetch(
        session,
        "SELECT id,is_locked,is_hidden,post_id,parent_id FROM community_comment"
        " WHERE id=:id FOR UPDATE",
        {"id": comment_id},
    )
    if not locked:
        raise LookupError(comment_id)
    return locked[0]


async def update_comment(
    session: AsyncSession, *, user_id: int, comment_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    row = await _mine(session, user_id, comment_id)
    if row.is_locked or row.is_hidden:
        raise PermissionError(comment_id)
    errors: dict[str, list[str]] = {}
    sets: list[str] = []
    params: dict[str, Any] = {"id": comment_id}
    if "content" in body:
        content = body["content"]
        if not isinstance(content, str):
            errors["content"] = ["Not a valid string."]
        elif not content.strip():
            errors["content"] = ["Comment content can not be blank."]
        elif len(content) > 5000:
            errors["content"] = ["Ensure this field has no more than 5000 characters."]
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
    if "is_spoiler" in body:
        sets.append("is_spoiler = :spoiler")
        params["spoiler"] = bool(body["is_spoiler"])
    if errors:
        raise ValueError(errors)
    if not sets:
        raise KeyError("no fields")
    await fetch(
        session,
        "UPDATE community_comment SET " + ", ".join(sets) + ", updated_at = now()"
        " WHERE id = :id RETURNING id",
        params,
    )
    await session.commit()
    return await comment_payload(
        await _comment_row(session, viewer_id=user_id, comment_id=comment_id)
    )


async def delete_comment(session: AsyncSession, *, user_id: int, comment_id: int) -> None:
    row = await _mine(session, user_id, comment_id)
    if row.is_locked or row.is_hidden:
        raise PermissionError(comment_id)
    replies = await fetch(
        session,
        "SELECT 1 FROM community_comment WHERE parent_id = :id LIMIT 1",
        {"id": comment_id},
    )
    if replies:
        await fetch(
            session,
            "UPDATE community_comment SET content = '', is_hidden = true,"
            " is_spoiler = false, updated_at = now() WHERE id = :id RETURNING id",
            {"id": comment_id},
        )
        await fetch(
            session,
            "UPDATE community_activity SET feed_policy='hidden' WHERE comment_id=:id RETURNING id",
            {"id": comment_id},
        )
    else:
        if row.post_id is not None:
            await fetch(
                session,
                "UPDATE community_post SET reply_count=GREATEST(0,reply_count-1)"
                " WHERE id=:id RETURNING id",
                {"id": row.post_id},
            )
        if row.parent_id is not None:
            await fetch(
                session,
                "UPDATE community_comment SET reply_count=GREATEST(0,reply_count-1)"
                " WHERE id=:id RETURNING id",
                {"id": row.parent_id},
            )
        await fetch(
            session,
            "DELETE FROM community_activity WHERE comment_id = :id RETURNING id",
            {"id": comment_id},
        )
        await fetch(
            session,
            "DELETE FROM community_comment WHERE id = :id RETURNING id",
            {"id": comment_id},
        )
    await session.commit()


async def moderate_comment(
    session: AsyncSession, *, moderator_id: int, comment_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    action = body.get("action_type")
    if action not in ("hide", "lock"):
        raise ValueError({"action_type": [f'"{action}" is not a valid choice.']})
    rows = await fetch(
        session,
        "SELECT id, author_id FROM community_comment WHERE id = :id",
        {"id": comment_id},
    )
    if not rows:
        raise LookupError(comment_id)
    if action == "hide":
        await fetch(
            session,
            "UPDATE community_comment SET is_hidden = true, updated_at = now()"
            " WHERE id = :id RETURNING id",
            {"id": comment_id},
        )
        await fetch(
            session,
            "UPDATE community_activity SET feed_policy = 'hidden'"
            " WHERE comment_id = :id RETURNING id",
            {"id": comment_id},
        )
    else:
        await fetch(
            session,
            "UPDATE community_comment SET is_locked = true, updated_at = now()"
            " WHERE id = :id RETURNING id",
            {"id": comment_id},
        )
    await fetch(
        session,
        "INSERT INTO community_moderation_action (moderator_id, target_user_id,"
        " comment_id, action_type, reason, metadata, created_at)"
        " VALUES (:moderator, :target_user, :comment, :action, :reason,"
        " '{}'::jsonb, now()) RETURNING id",
        {
            "moderator": moderator_id,
            "target_user": rows[0].author_id,
            "comment": comment_id,
            "action": action,
            "reason": body.get("reason", "") or "",
        },
    )
    await session.commit()
    return await comment_payload(
        await _comment_row(session, viewer_id=moderator_id, comment_id=comment_id)
    )
