"""Replacing the weekly board in one transaction.

The live schema constrains this in two ways that shape the code:

* `airing_board` has a **partial unique index on `status = 'active'`**, so the previous
  board must be archived *before* the new one is inserted — two independent inserts fail.
* `airing_event` uniqueness includes `observation_id`, so events are history: a new
  observation adds a new generation rather than overwriting the last one.

Nothing here deletes: the previous board and its events stay readable, which is what lets a
later run report what changed.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

ACTIVE = "active"
ARCHIVED = "archived"


async def archive_active_boards(session: AsyncSession) -> int:
    rows = await fetch(
        session,
        "UPDATE airing_board SET status = :archived, updated_at = now()"
        " WHERE status = :active RETURNING id",
        {"archived": ARCHIVED, "active": ACTIVE},
    )
    return len(rows)


async def create_board(
    session: AsyncSession,
    *,
    season_key: str,
    observation_id: Any,
    item_count: int,
    metadata: dict[str, Any] | None = None,
    effective_from: date | None = None,
    effective_until: date | None = None,
) -> Any:
    rows = await fetch(
        session,
        """
        INSERT INTO airing_board
          (id, season_key, status, item_count, metadata, effective_from,
           effective_until, observation_id, created_at, updated_at)
        VALUES (gen_random_uuid(), :season, :status, :count, CAST(:metadata AS jsonb),
                :from_date, :until_date, :observation, now(), now())
        RETURNING id
        """,
        {
            "season": season_key,
            "status": ACTIVE,
            "count": max(0, int(item_count)),
            "metadata": json.dumps(metadata or {}),
            "from_date": effective_from,
            "until_date": effective_until,
            "observation": observation_id,
        },
    )
    return rows[0].id


async def add_events(
    session: AsyncSession,
    *,
    observation_id: Any,
    events: list[dict[str, Any]],
) -> int:
    """Append one generation of events for an observation.

    Each event: ``work_id``, ``collection_doing``, ``timezone``, ``region``,
    ``precision``, ``raw_value`` and optionally ``starts_at``, ``weekday``,
    ``episode_entity_id``.
    """
    if not events:
        return 0
    payload = json.dumps(
        [
            {
                "work_id": str(event["work_id"]),
                "collection_doing": int(event.get("collection_doing", 0)),
                "timezone": event.get("timezone") or "Asia/Tokyo",
                "region": event.get("region") or "",
                "weekday": event.get("weekday"),
                "precision": event.get("precision") or "unknown",
                "raw_value": event.get("raw_value") or "",
                "starts_at": event.get("starts_at").isoformat()
                if isinstance(event.get("starts_at"), datetime)
                else event.get("starts_at"),
                "episode_entity_id": str(event["episode_entity_id"])
                if event.get("episode_entity_id")
                else None,
            }
            for event in events
        ]
    )
    rows = await fetch(
        session,
        """
        INSERT INTO airing_event
          (starts_at, timezone, region, weekday, precision, raw_value,
           episode_entity_id, observation_id, work_id, collection_doing,
           created_at, updated_at)
        SELECT e.starts_at, e.timezone, e.region, e.weekday,
               e.precision, e.raw_value, e.episode_entity_id, :observation,
               e.work_id, e.collection_doing, now(), now()
        FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS e(
          work_id uuid, collection_doing integer, timezone text, region text,
          weekday integer, precision text, raw_value text,
          starts_at timestamptz, episode_entity_id uuid)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        {"rows": payload, "observation": observation_id},
    )
    return len(rows)


async def replace_board(
    session: AsyncSession,
    *,
    season_key: str,
    observation_id: Any,
    events: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    effective_from: date | None = None,
    effective_until: date | None = None,
) -> dict[str, Any]:
    """Archive the active board, create the next one, then record its events."""
    archived = await archive_active_boards(session)
    board_id = await create_board(
        session,
        season_key=season_key,
        observation_id=observation_id,
        item_count=len(events),
        metadata=metadata,
        effective_from=effective_from,
        effective_until=effective_until,
    )
    written = await add_events(session, observation_id=observation_id, events=events)
    return {"archived": archived, "events": written, "board_id": board_id}


__all__ = [
    "ACTIVE",
    "ARCHIVED",
    "add_events",
    "archive_active_boards",
    "create_board",
    "replace_board",
]
