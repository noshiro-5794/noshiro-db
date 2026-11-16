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


__all__ = ["SUPPORTED_PROVIDER_SLUGS", "AiringTarget", "board_targets"]
