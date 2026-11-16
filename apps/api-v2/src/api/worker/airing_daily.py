"""Which records the daily refresh should touch, for the board that is on air.

Ported from `AiringDailySyncService.board_targets`. The selection is the part worth
comparing first: it decides which of the three providers' records get refreshed every day,
and a different answer means a different slice of the board goes stale.

The rule is: take the works on the active board — from its observation **and** from any
explicit board entries — then their active representations at a supported provider, one
target per ``provider:external_id``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

SUPPORTED_PROVIDER_SLUGS = ("bangumi", "anilist", "mal")


@dataclass(frozen=True)
class AiringTarget:
    provider_slug: str
    external_id: str
    work_id: Any


async def board_targets(session: AsyncSession) -> tuple[list[AiringTarget], str | None]:
    boards = await fetch(
        session,
        "SELECT id, season_key, observation_id FROM airing_board WHERE status = 'active' LIMIT 1",
        {},
    )
    if not boards:
        return [], None
    board = boards[0]
    work_ids: set[Any] = set()
    if board.observation_id is not None:
        rows = await fetch(
            session,
            "SELECT DISTINCT work_id FROM airing_event WHERE observation_id = :o",
            {"o": board.observation_id},
        )
        work_ids.update(row.work_id for row in rows)
    entries = await fetch(
        session,
        "SELECT DISTINCT work_id FROM airing_board_entry WHERE board_id = :b",
        {"b": board.id},
    )
    work_ids.update(row.work_id for row in entries)
    if not work_ids:
        return [], board.season_key

    rows = await fetch(
        session,
        """
        SELECT p.slug AS provider_slug, r.external_id AS external_id,
               rep.entity_id AS work_id
        FROM entity_representation AS rep
        JOIN provider_record AS r ON r.id = rep.provider_record_id
        JOIN provider_namespace AS ns ON ns.id = r.namespace_id
        JOIN provider AS p ON p.id = ns.provider_id
        WHERE rep.entity_id = ANY(:works) AND rep.is_active
          AND r.status = 'active' AND p.slug = ANY(:providers)
        ORDER BY r.external_id
        """,
        {"works": list(work_ids), "providers": list(SUPPORTED_PROVIDER_SLUGS)},
    )
    seen: set[str] = set()
    targets: list[AiringTarget] = []
    for row in rows:
        key = f"{row.provider_slug}:{row.external_id}"
        if key in seen:
            continue
        seen.add(key)
        targets.append(
            AiringTarget(
                provider_slug=row.provider_slug,
                external_id=row.external_id,
                work_id=row.work_id,
            )
        )
    targets.sort(key=lambda item: (item.provider_slug, item.external_id))
    return targets, board.season_key


TASK_NAME = "airing_daily"
DEFAULT_SHARD = "airing"
IDLE = "idle"
RUNNING = "running"
FINISHED = "finished"
FAILED = "failed"


def shard_for(now: Any, *, season_key: str | None = None) -> str:
    """The state row for one day of one season: ``airing_daily:<date>:<season>``.

    A new date starts a new shard, and a season rollover changes the suffix, which is what
    makes the window restart without anyone clearing anything.
    """
    date_part = now.date().isoformat() if hasattr(now, "date") else str(now)[:10]
    suffix = (season_key or "").strip() or DEFAULT_SHARD
    return f"{TASK_NAME}:{date_part}:{suffix}"


async def start_window(
    session: AsyncSession, *, shard: str, total_count: int, batch_size: int
) -> tuple[int, int] | None:
    """Claim the next batch, or None when a window is already running."""
    rows = await fetch(
        session,
        "SELECT id, current_id, status FROM sync_state"
        " WHERE task_name = :task AND shard = :shard FOR UPDATE",
        {"task": TASK_NAME, "shard": shard},
    )
    if not rows:
        await fetch(
            session,
            "INSERT INTO sync_state (task_name, shard, current_id, end_id, status,"
            " fail_count, updated_at) VALUES (:task, :shard, 0, 0, :idle, 0, now())"
            " RETURNING id",
            {"task": TASK_NAME, "shard": shard, "idle": IDLE},
        )
        current_id = 0
        status = IDLE
    else:
        current_id = rows[0].current_id
        status = rows[0].status
    if status == RUNNING:
        return None
    start = min(current_id, total_count - 1)
    end = min(start + max(1, batch_size) - 1, total_count - 1)
    await fetch(
        session,
        "UPDATE sync_state SET end_id = :end, status = :running, updated_at = now()"
        " WHERE task_name = :task AND shard = :shard RETURNING id",
        {"end": end, "running": RUNNING, "task": TASK_NAME, "shard": shard},
    )
    return start, end


async def finish_window(
    session: AsyncSession, *, shard: str, current_id: int, finished: bool
) -> None:
    await fetch(
        session,
        "UPDATE sync_state SET current_id = :current, status = :status,"
        " updated_at = now() WHERE task_name = :task AND shard = :shard RETURNING id",
        {
            "current": current_id,
            "status": FINISHED if finished else IDLE,
            "task": TASK_NAME,
            "shard": shard,
        },
    )


async def fail_window(session: AsyncSession, *, shard: str, current_id: int) -> None:
    await fetch(
        session,
        "UPDATE sync_state SET current_id = :current, status = :failed,"
        " fail_count = fail_count + 1, updated_at = now()"
        " WHERE task_name = :task AND shard = :shard RETURNING id",
        {"current": current_id, "failed": FAILED, "task": TASK_NAME, "shard": shard},
    )


__all__ = [
    "DEFAULT_SHARD",
    "FINISHED",
    "IDLE",
    "RUNNING",
    "SUPPORTED_PROVIDER_SLUGS",
    "AiringTarget",
    "board_targets",
    "fail_window",
    "finish_window",
    "shard_for",
    "start_window",
]
