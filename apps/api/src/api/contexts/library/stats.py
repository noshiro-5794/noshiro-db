"""What a year of someone's library looks like.

Every day boundary is the user's, not the server's: the timestamp is converted to
their zone before it is truncated, which is the difference between a mark landing
on the 31st or the 1st.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


def window(year: int, zone: ZoneInfo) -> tuple[datetime, datetime]:
    return (
        datetime(year, 1, 1, tzinfo=zone),
        datetime(year + 1, 1, 1, tzinfo=zone),
    )


async def stats(
    session: AsyncSession, *, user_id: int, year: int, zone: ZoneInfo
) -> dict[str, Any]:
    start, end = window(year, zone)
    tz = str(zone)
    years = await fetch(
        session,
        "SELECT DISTINCT EXTRACT(YEAR FROM created_at AT TIME ZONE :tz)::int AS year"
        " FROM user_library_entry WHERE user_id = :user_id ORDER BY year DESC",
        {"tz": tz, "user_id": user_id},
    )
    totals = await fetch(
        session,
        """
        SELECT
            (SELECT count(*) FROM user_library_entry WHERE user_id = :user_id)
                AS subjects,
            (SELECT count(*) FROM user_review AS review
               JOIN user_library_entry AS entry
                 ON entry.id = review.user_subject_id
              WHERE entry.user_id = :user_id) AS reviews,
            (SELECT count(*) FROM user_collection WHERE user_id = :user_id)
                AS collections,
            (SELECT count(*) FROM user_library_entry
              WHERE user_id = :user_id
                AND created_at >= :start AND created_at < :end) AS marks_in_year
        """,
        {"user_id": user_id, "start": start, "end": end},
    )
    calendar = await fetch(
        session,
        """
        SELECT to_char(created_at AT TIME ZONE :tz, 'YYYY-MM-DD') AS day,
               count(*) AS count
        FROM user_library_entry
        WHERE user_id = :user_id AND created_at >= :start AND created_at < :end
        GROUP BY 1 ORDER BY 1
        """,
        {"tz": tz, "user_id": user_id, "start": start, "end": end},
    )
    row = totals[0]
    return {
        "year": year,
        "available_years": [item.year for item in years],
        "totals": {
            "subjects": int(row.subjects),
            "reviews": int(row.reviews),
            "collections": int(row.collections),
            "marks_in_year": int(row.marks_in_year),
        },
        "mark_calendar": [{"date": item.day, "count": int(item.count)} for item in calendar],
    }
