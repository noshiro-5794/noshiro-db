"""Reports a user filed about posts, comments, reviews, collections or activities.

The payload names the target by the one foreign key that is set, and carries the
people involved so a client can render the row without a second request.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.community.people import person as _person
from api.contexts.presentation.fragments import fetch

TARGETS = ("post", "comment", "review", "collection", "activity")


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
