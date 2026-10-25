"""The calendar: airing events for a date range, or the current weekly board.

Two shapes share one payload. With a range, events are the precise per-episode
rows and the answer is ordered by time. Without one, the answer is the weekly
board: the active board's weekday rows plus AniList schedules the board does not
own, collapsed to one slot per work and ordered by weekday and popularity.

Identity is resolved in memory from one redirect map, the way the Django view
does it, because a page can hold hundreds of events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .fragments import (
    CURRENT,
    PROVENANCE,
    PROVENANCE_JOINS,
    fetch,
    isoformat,
    row_provenance,
)
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

EVENT_COLUMNS = """
    event.id, event.work_id AS work_entity_id, event.episode_entity_id,
    event.starts_at, event.timezone, event.region, event.weekday,
    event.precision, event.raw_value, event.collection_doing
"""

EVENT_JOINS = f"""
    JOIN work ON work.entity_id = event.work_id
    JOIN entity AS work_entity ON work_entity.id = event.work_id
    {
    PROVENANCE_JOINS.format(
        record="observation.provider_record_id",
        observation="event.observation_id",
    )
}
"""

CURRENT_EVENT = CURRENT.format(
    record="observation.provider_record_id", observation="event.observation_id"
)

VISIBLE_WORK = "work_entity.lifecycle = 'active' AND work_entity.visibility = 'public'"


async def _events(session: AsyncSession, sql: str, params: dict[str, Any]) -> list[Any]:
    return await fetch(
        session,
        f"SELECT {EVENT_COLUMNS}, {PROVENANCE} FROM airing_event AS event {EVENT_JOINS}"
        f" WHERE {sql}",
        params,
    )


async def _range_events(
    session: AsyncSession,
    *,
    start: datetime | None,
    end: datetime | None,
    timezone: str,
) -> list[Any]:
    clauses = [
        CURRENT_EVENT,
        VISIBLE_WORK,
        "event.starts_at IS NOT NULL",
        "event.precision IN ('minute', 'day')",
    ]
    params: dict[str, Any] = {}
    if start is not None:
        clauses.append("event.starts_at >= :start")
        params["start"] = start
    if end is not None:
        clauses.append("event.starts_at <= :end")
        params["end"] = end
    if timezone:
        clauses.append("event.timezone = :timezone")
        params["timezone"] = timezone
    return await _events(
        session,
        " AND ".join(clauses) + " ORDER BY event.starts_at, event.id",
        params,
    )


async def _board_events(session: AsyncSession) -> list[Any]:
    board = await fetch(
        session,
        "SELECT observation_id FROM airing_board WHERE status = 'active' ORDER BY id LIMIT 1",
        {},
    )
    if board and board[0].observation_id is not None:
        return await _events(
            session,
            f"{CURRENT_EVENT} AND {VISIBLE_WORK}"
            " AND event.observation_id = :board AND event.precision = 'weekday'"
            " ORDER BY event.weekday, event.collection_doing DESC, event.id",
            {"board": board[0].observation_id},
        )
    return await _events(
        session,
        f"{CURRENT_EVENT} AND {VISIBLE_WORK} AND event.precision = 'weekday'"
        " ORDER BY event.weekday, event.collection_doing DESC, event.id",
        {},
    )


async def _supplementary_events(session: AsyncSession) -> list[Any]:
    return await _events(
        session,
        f"{CURRENT_EVENT} AND {VISIBLE_WORK}"
        " AND event.precision = 'minute' AND event.starts_at >= now()"
        " AND work.work_type = 'anime'"
        " AND provider.slug = 'anilist' AND namespace.slug = 'calendar'",
        {},
    )


async def calendar_events(
    session: AsyncSession,
    *,
    start: datetime | None,
    end: datetime | None,
    timezone: str,
    include_work: bool,
) -> list[dict[str, Any]]:
    has_range = start is not None or end is not None
    if has_range:
        ordered = await _range_events(session, start=start, end=end, timezone=timezone)
    else:
        ordered = await _board_events(session) + await _supplementary_events(session)
        ordered.sort(
            key=lambda event: (
                event.weekday if event.weekday is not None else 7,
                -event.collection_doing,
                str(event.work_entity_id),
            )
        )

    resolved = await load_redirects(session)

    if not has_range:
        collapsed: dict[UUID, Any] = {}
        for event in ordered:
            root = root_of(event.work_entity_id, resolved)
            current = collapsed.get(root)
            if current is None or (event.precision == "minute" and current.precision != "minute"):
                collapsed[root] = event
        ordered = list(collapsed.values())

    work_roots = {root_of(event.work_entity_id, resolved) for event in ordered}
    episode_roots = {
        root_of(event.episode_entity_id, resolved)
        for event in ordered
        if event.episode_entity_id is not None
    }
    grouped = build_clusters(work_roots | episode_roots, resolved)
    member_ids = {member for members in grouped.values() for member in members}
    entities = await load_entities(session, member_ids)

    # The summary is built whether or not it is returned: it decides whether a
    # work may appear at all, and hides adult works.
    summaries: dict[UUID, dict[str, Any]] = {}
    for root in work_roots:
        if root in entities:
            summaries[root] = await entity_summary(
                session,
                root=root,
                cluster_ids=[str(value) for value in grouped.get(root, {root})],
                language="",
                cluster_scope=False,
            )

    data: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for event in ordered:
        work_root = root_of(event.work_entity_id, resolved)
        if work_root not in entities or not publicly_visible(work_root, grouped, entities):
            continue
        summary = summaries.get(work_root)
        if summary is None or summary["audience"] == "adult":
            continue
        episode_id = None
        if event.episode_entity_id is not None:
            episode_root = root_of(event.episode_entity_id, resolved)
            if episode_root not in entities or not publicly_visible(
                episode_root, grouped, entities
            ):
                continue
            episode_id = str(episode_root)
        key = (
            work_root,
            event.weekday,
            event.region,
            episode_id if has_range else None,
            event.starts_at if has_range else None,
        )
        if key in seen:
            continue
        seen.add(key)
        payload: dict[str, Any] = {
            "id": event.id,
            "work_id": str(work_root),
            "episode_id": episode_id,
            "starts_at": isoformat(event.starts_at),
            "timezone": event.timezone,
            "region": event.region,
            "weekday": event.weekday,
            "precision": event.precision,
            "raw_value": event.raw_value,
            "collection_doing": event.collection_doing,
            "provenance": row_provenance(event),
            # DRF renders a nullable field that is absent as null, so the key is
            # always there.
            "work": summary if include_work else None,
        }
        data.append(payload)
    return data
