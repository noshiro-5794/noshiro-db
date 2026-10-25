"""The Gantt board: one bar per canonical work and weekday.

Bars are the curated projection — after identity resolution there is exactly one
entry per work, weekday and slot, with `source_refs` recording which provider
observations support it. The window is rolling (previous, current and next month)
because a schedule is only trustworthy near the present.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import fetch, isoformat
from .identity import (
    clusters as build_clusters,
)
from .identity import (
    load_entities,
    load_redirects,
    publicly_visible,
    root_of,
)
from .summary import entity_summary

TOKYO = ZoneInfo("Asia/Tokyo")


def add_months(value: date, months: int) -> date:
    index = value.month - 1 + months
    return date(value.year + index // 12, index % 12 + 1, 1)


def window_dates() -> tuple[date, date]:
    today = datetime.now(TOKYO).date()
    first = date(today.year, today.month, 1)
    return add_months(first, -1), add_months(first, 2) - timedelta(days=1)


async def board_entries(session: AsyncSession, *, include_work: bool) -> list[dict[str, Any]]:
    board = await fetch(
        session,
        "SELECT id, season_key FROM airing_board WHERE status = 'active' ORDER BY id LIMIT 1",
        {},
    )
    if not board:
        return []
    window_start, window_end = window_dates()
    rows = await fetch(
        session,
        """
        SELECT entry.id, entry.work_id, entry.episode_entity_id,
               entry.episode_number, entry.starts_at, entry.duration_minutes,
               entry.timezone, entry.region, entry.weekday, entry.precision,
               entry.status, entry.decision, entry.confidence, entry.source_refs
        FROM airing_board_entry AS entry
        WHERE entry.board_id = CAST(:board AS uuid)
        ORDER BY entry.weekday, entry.starts_at, entry.work_id
        """,
        {"board": str(board[0].id)},
    )
    resolved = await load_redirects(session)
    work_roots = {root_of(row.work_id, resolved) for row in rows}
    grouped = build_clusters(work_roots, resolved)
    member_ids = {member for members in grouped.values() for member in members}
    entities = await load_entities(session, member_ids)

    visible: list[tuple[Any, UUID]] = []
    for row in rows:
        root = root_of(row.work_id, resolved)
        entity = entities.get(root)
        if (
            entity is None
            or entity.lifecycle != "active"
            or not publicly_visible(root, grouped, entities)
        ):
            continue
        visible.append((row, root))

    summaries: dict[UUID, dict[str, Any]] = {}
    for _, root in visible:
        summaries[root] = await entity_summary(
            session,
            root=root,
            cluster_ids=[str(value) for value in grouped.get(root, {root})],
            language="",
            cluster_scope=False,
        )
    visible = [(row, root) for row, root in visible if summaries[root]["audience"] != "adult"]
    profiles = {
        row.work_id: row
        for row in await fetch(
            session,
            "SELECT work_id, format, premiered_on, ended_on, episode_count"
            " FROM anime_profile WHERE work_id = ANY(CAST(:ids AS uuid[]))",
            {"ids": [str(root) for _, root in visible]},
        )
    }

    data: list[dict[str, Any]] = []
    for row, root in visible:
        summary = summaries[root]
        profile = profiles.get(root)
        row_format = profile.format if profile is not None else ""
        starts_at = row.starts_at
        ends_at = None
        if starts_at is not None and row.duration_minutes:
            ends_at = starts_at + timedelta(minutes=row.duration_minutes)
        data.append(
            {
                "id": str(row.id),
                "season_key": board[0].season_key,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "work_id": str(root),
                "episode_entity_id": (
                    str(row.episode_entity_id) if row.episode_entity_id else None
                ),
                "episode_number": row.episode_number,
                "starts_at": isoformat(starts_at),
                "ends_at": isoformat(ends_at),
                "timezone": row.timezone,
                "region": row.region,
                "weekday": row.weekday,
                "duration_minutes": row.duration_minutes,
                "precision": row.precision,
                "format": str(row_format or ""),
                "premiered_on": (
                    profile.premiered_on.isoformat()
                    if profile is not None and profile.premiered_on
                    else None
                ),
                "ended_on": (
                    profile.ended_on.isoformat()
                    if profile is not None and profile.ended_on
                    else None
                ),
                "episode_count": profile.episode_count if profile is not None else None,
                "status": row.status,
                "decision": row.decision,
                "confidence": float(row.confidence),
                "source_refs": row.source_refs,
                "work": summary if include_work else None,
            }
        )
    return data
