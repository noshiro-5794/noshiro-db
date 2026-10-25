"""Reports a user filed about posts, comments, reviews, collections or activities.

The payload names the target by the one foreign key that is set, and carries the
people involved so a client can render the row without a second request.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.community.people import person as _person
from api.contexts.community.visibility import visible
from api.contexts.presentation.fragments import fetch

TARGETS = ("post", "comment", "review", "collection", "activity")
REASONS = ("spam", "harassment", "spoiler", "illegal", "other")
OWNERS = {
    "post": ("community_post", "author_id"),
    "comment": ("community_comment", "author_id"),
    "collection": ("user_collection", "user_id"),
    "activity": ("community_activity", "user_id"),
}
NOT_CHOICE = '"{}" is not a valid choice.'
TARGET_NOT_FOUND = "Community target not found."

REPORT_QUERY = """
    SELECT report.id, report.reason, report.description, report.status,
           report.resolved_at, report.created_at,
           report.post_id, report.comment_id, report.review_id,
           report.collection_id, report.activity_id,
           reporter.id AS reporter_id, reporter_profile.nickname AS reporter_nickname,
           reporter_profile.avatar AS reporter_avatar,
           reported.id AS reported_user_id,
           reported_profile.nickname AS reported_nickname,
           reported_profile.avatar AS reported_avatar,
           resolver.id AS resolver_id, resolver_profile.nickname AS resolver_nickname,
           resolver_profile.avatar AS resolver_avatar
    FROM community_report AS report
    JOIN "user" AS reporter ON reporter.id = report.reporter_id
    LEFT JOIN user_profile AS reporter_profile ON reporter_profile.user_id = reporter.id
    LEFT JOIN "user" AS reported ON reported.id = report.reported_user_id
    LEFT JOIN user_profile AS reported_profile
      ON reported_profile.user_id = reported.id
    LEFT JOIN "user" AS resolver ON resolver.id = report.resolved_by_id
    LEFT JOIN user_profile AS resolver_profile
      ON resolver_profile.user_id = resolver.id
"""


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


def _target(report: Any) -> dict[str, Any] | None:
    for kind in TARGETS:
        value = getattr(report, f"{kind}_id")
        if value is not None:
            return {"type": kind, "id": value}
    return None


async def list_reports(
    session: AsyncSession,
    *,
    user_id: int | None,
    status: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    where = ["TRUE"]
    params: dict[str, Any] = {}
    if user_id is not None:
        where.append("report.reporter_id = :user_id")
        params["user_id"] = user_id
    if status:
        where.append("report.status = :status")
        params["status"] = status
    clause = " AND ".join(where)
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM community_report AS report WHERE {clause}",
        params,
    )
    rows = await fetch(
        session,
        f"""
        SELECT report.id, report.reason, report.description, report.status,
               report.resolved_at, report.created_at,
               report.post_id, report.comment_id, report.review_id,
               report.collection_id, report.activity_id,
               reporter.id AS reporter_id, reporter_profile.nickname AS reporter_nickname,
               reporter_profile.avatar AS reporter_avatar,
               reported.id AS reported_user_id,
               reported_profile.nickname AS reported_nickname,
               reported_profile.avatar AS reported_avatar,
               resolver.id AS resolver_id, resolver_profile.nickname AS resolver_nickname,
               resolver_profile.avatar AS resolver_avatar
        FROM community_report AS report
        JOIN "user" AS reporter ON reporter.id = report.reporter_id
        LEFT JOIN user_profile AS reporter_profile
          ON reporter_profile.user_id = reporter.id
        LEFT JOIN "user" AS reported ON reported.id = report.reported_user_id
        LEFT JOIN user_profile AS reported_profile
          ON reported_profile.user_id = reported.id
        LEFT JOIN "user" AS resolver ON resolver.id = report.resolved_by_id
        LEFT JOIN user_profile AS resolver_profile
          ON resolver_profile.user_id = resolver.id
        WHERE {clause}
        ORDER BY report.created_at DESC, report.id DESC
        LIMIT :limit OFFSET :offset
        """,
        {
            **params,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    return int(total[0].total), [
        {
            "id": row.id,
            "reason": row.reason,
            "description": row.description,
            "status": row.status,
            "reporter": _person(row.reporter_id, row.reporter_nickname, row.reporter_avatar),
            "reported_user": _person(
                row.reported_user_id, row.reported_nickname, row.reported_avatar
            ),
            "target": _target(row),
            "resolved_by": _person(row.resolver_id, row.resolver_nickname, row.resolver_avatar),
            "resolved_at": _iso(row.resolved_at),
            "created_at": _iso(row.created_at),
        }
        for row in rows
    ]


async def list_my_reports(
    session: AsyncSession, *, user_id: int, page: int, page_size: int
) -> tuple[int, list[dict[str, Any]]]:
    return await list_reports(session, user_id=user_id, status="", page=page, page_size=page_size)


async def report_payload(session: AsyncSession, report_id: int) -> dict[str, Any]:
    rows = await fetch(session, REPORT_QUERY + " WHERE report.id = :id", {"id": report_id})
    return _payload(rows[0])


def _payload(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "reason": row.reason,
        "description": row.description,
        "status": row.status,
        "reporter": _person(row.reporter_id, row.reporter_nickname, row.reporter_avatar),
        "reported_user": _person(row.reported_user_id, row.reported_nickname, row.reported_avatar),
        "target": _target(row),
        "resolved_by": _person(row.resolver_id, row.resolver_nickname, row.resolver_avatar),
        "resolved_at": _iso(row.resolved_at),
        "created_at": _iso(row.created_at),
    }


async def _owner(session: AsyncSession, target_type: str, target_id: Any) -> Any:
    if target_type == "review":
        rows = await fetch(
            session,
            "SELECT entry.user_id FROM user_review AS review"
            " JOIN user_library_entry AS entry ON entry.id = review.user_subject_id"
            " WHERE review.id = :id",
            {"id": target_id},
        )
        return rows[0].user_id if rows else None
    table, column = OWNERS[target_type]
    rows = await fetch(
        session,
        f"SELECT {column} AS owner_id FROM {table} WHERE id = :id",
        {"id": target_id},
    )
    return rows[0].owner_id if rows else None


async def create_report(
    session: AsyncSession, *, reporter_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    errors: dict[str, list[str]] = {}
    target_type = body.get("target_type")
    if target_type not in TARGETS:
        errors["target_type"] = [NOT_CHOICE.format(target_type)]
    reason = body.get("reason")
    if reason not in REASONS:
        errors["reason"] = [NOT_CHOICE.format(reason)]
    description = body.get("description", "")
    if not isinstance(description, str):
        errors["description"] = ["Not a valid string."]
    elif len(description) > 2000:
        errors["description"] = ["Ensure this field has no more than 2000 characters."]
    target_id = body.get("target_id")
    if not isinstance(target_id, int) or isinstance(target_id, bool) or target_id < 1:
        errors["target_id"] = ["A valid integer is required."]
    if errors:
        raise ValueError(errors)
    owner = await _owner(session, str(target_type), target_id)
    if owner is None or not await visible(session, str(target_type), target_id):
        raise FileNotFoundError(target_type)
    column = f"{target_type}_id"
    rows = await fetch(
        session,
        "INSERT INTO community_report (reason, description, status, created_at,"
        f" reporter_id, reported_user_id, {column})"
        " VALUES (:reason, :description, 'pending', now(), :reporter_id,"
        " :owner, :target_id) RETURNING id",
        {
            "reason": reason,
            "description": description,
            "reporter_id": reporter_id,
            "owner": owner,
            "target_id": target_id,
        },
    )
    await session.commit()
    return await report_payload(session, rows[0].id)


STATUSES = ("pending", "accepted", "rejected")


async def resolve_report(
    session: AsyncSession, *, moderator_id: int, report_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    status = body.get("status")
    if status not in STATUSES:
        raise ValueError({"status": [f'"{status}" is not a valid choice.']})
    action = body.get("action_type")
    if action is not None and action not in ("hide", "lock"):
        raise ValueError({"action_type": [f'"{action}" is not a valid choice.']})
    rows = await fetch(
        session,
        "SELECT id, status, post_id, comment_id, activity_id, review_id,"
        " collection_id FROM community_report WHERE id = :id",
        {"id": report_id},
    )
    if not rows:
        raise LookupError(report_id)
    report = rows[0]
    if report.status != "pending":
        raise RuntimeError("resolved")
    await fetch(
        session,
        "UPDATE community_report SET status = :status, resolved_by_id = :moderator,"
        " resolved_at = now() WHERE id = :id RETURNING id",
        {"status": status, "moderator": moderator_id, "id": report_id},
    )
    if action is not None:
        await _apply_action(session, moderator_id, report, action, body)
    await session.commit()
    return await report_payload(session, report_id)


async def _apply_action(
    session: AsyncSession, moderator_id: int, report: Any, action: str, body: Any
) -> None:
    reason = body.get("moderation_reason", "") or ""
    target_id = None
    target_user = None
    column = ""
    if report.post_id is not None:
        column = "post_id"
        target_id = report.post_id
        rows = await fetch(
            session,
            "SELECT author_id FROM community_post WHERE id = :id",
            {"id": target_id},
        )
        target_user = rows[0].author_id if rows else None
        sets = "feed_policy = 'hidden'" if action == "hide" else "is_locked = true"
        await fetch(
            session,
            f"UPDATE community_post SET {sets}, updated_at = now() WHERE id = :id RETURNING id",
            {"id": target_id},
        )
        if action == "hide":
            await fetch(
                session,
                "UPDATE community_activity SET feed_policy = 'hidden'"
                " WHERE post_id = :id RETURNING id",
                {"id": target_id},
            )
    elif report.comment_id is not None:
        column = "comment_id"
        target_id = report.comment_id
        rows = await fetch(
            session,
            "SELECT author_id FROM community_comment WHERE id = :id",
            {"id": target_id},
        )
        target_user = rows[0].author_id if rows else None
        sets = "is_hidden = true" if action == "hide" else "is_locked = true"
        await fetch(
            session,
            f"UPDATE community_comment SET {sets}, updated_at = now() WHERE id = :id RETURNING id",
            {"id": target_id},
        )
        if action == "hide":
            await fetch(
                session,
                "UPDATE community_activity SET feed_policy = 'hidden'"
                " WHERE comment_id = :id RETURNING id",
                {"id": target_id},
            )
    elif report.activity_id is not None:
        column = "activity_id"
        target_id = report.activity_id
        rows = await fetch(
            session,
            "SELECT user_id FROM community_activity WHERE id = :id",
            {"id": target_id},
        )
        target_user = rows[0].user_id if rows else None
        if action == "hide":
            await fetch(
                session,
                "UPDATE community_activity SET feed_policy = 'hidden' WHERE id = :id RETURNING id",
                {"id": target_id},
            )
    if column:
        await fetch(
            session,
            "INSERT INTO community_moderation_action (moderator_id, target_user_id,"
            f" {column}, report_id, action_type, reason, metadata, created_at)"
            " VALUES (:moderator, :target_user, :target, :report, :action, :reason,"
            " '{}'::jsonb, now()) RETURNING id",
            {
                "moderator": moderator_id,
                "target_user": target_user,
                "target": target_id,
                "report": report.id,
                "action": action,
                "reason": reason,
            },
        )
