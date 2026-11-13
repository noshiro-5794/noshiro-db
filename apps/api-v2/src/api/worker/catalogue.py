"""Popularity ranking, ported from `apps/index/services/popularity.py`.

The score is a percentile inside one source's own series, so a rebuild touches every
work: a single new record shifts the standing of everything else. That is why the port
recomputes the table rather than patching rows.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

SCORE_SCALE = Decimal("100")

# The one source whose number ranks each catalogue type.
PRIMARY_SIGNALS = (
    ("anime", "anilist", "popularity"),
    ("galgame", "vndb", "votes"),
)


async def _redirect_map(session: AsyncSession) -> dict[Any, Any]:
    rows = await fetch(
        session,
        "SELECT source_entity_id, target_entity_id FROM entity_redirect WHERE is_active",
        {},
    )
    return {row.source_entity_id: row.target_entity_id for row in rows}


def _resolve(redirects: dict[Any, Any], entity_id: Any) -> Any:
    current = entity_id
    seen: set[Any] = set()
    for _ in range(32):
        if current in seen:
            return entity_id
        seen.add(current)
        target = redirects.get(current)
        if target is None:
            return current
        current = target
    return entity_id


async def _rank(session: AsyncSession, *, work_type: str, source: str, metric: str) -> list[Any]:
    """The latest value per entity inside one source's series."""
    return await fetch(
        session,
        """
        SELECT DISTINCT ON (m.entity_id) m.entity_id, m.value
        FROM metric_snapshot AS m
        JOIN provider_record AS r ON r.id = m.provider_record_id
        JOIN provider_namespace AS ns ON ns.id = r.namespace_id
        JOIN provider AS p ON p.id = ns.provider_id
        WHERE m.metric = :metric AND p.slug = :source
          AND EXISTS (
            SELECT 1 FROM work AS w
            WHERE w.entity_id = m.entity_id AND w.work_type = :work_type
          )
        ORDER BY m.entity_id, m.observed_at DESC
        """,
        {"metric": metric, "source": source, "work_type": work_type},
    )


async def refresh(session: AsyncSession, *, now: datetime) -> int:
    redirects = await _redirect_map(session)
    latest: dict[Any, Decimal] = {}
    for work_type, source, metric in PRIMARY_SIGNALS:
        for row in await _rank(session, work_type=work_type, source=source, metric=metric):
            root = _resolve(redirects, row.entity_id)
            current = latest.get(root)
            if current is None or Decimal(str(row.value)) > current:
                latest[root] = Decimal(str(row.value))
    if not latest:
        return 0
    return await _persist(session, latest, now=now)


async def _persist(session: AsyncSession, latest: dict[Any, Decimal], *, now: datetime) -> int:
    ordered = sorted(latest.items(), key=lambda item: (item[1], str(item[0])))
    denominator = len(ordered) - 1
    scores: dict[Any, Decimal] = {}
    previous_value: Decimal | None = None
    previous_rank = Decimal(0)
    for index, (entity_id, value) in enumerate(ordered):
        if value == previous_value:
            # Equal reach is an equal standing; sharing the lower rank keeps the
            # order stable instead of inventing a difference.
            rank = previous_rank
        elif denominator <= 0:
            rank = Decimal(1)
        else:
            rank = Decimal(index) / Decimal(denominator)
        previous_value, previous_rank = value, rank
        scores[entity_id] = (rank * SCORE_SCALE).quantize(Decimal("0.000001"))
    scorable = await fetch(
        session,
        "SELECT id FROM entity WHERE id = ANY(:ids)"
        " AND lifecycle = 'active' AND visibility = 'public'",
        {"ids": list(scores)},
    )
    scorable_ids = {row.id for row in scorable}
    if not scorable_ids:
        return 0
    payload = json.dumps(
        [{"entity_id": str(key), "score": str(scores[key])} for key in scorable_ids]
    )
    await fetch(
        session,
        "UPDATE work SET popularity = v.score, popularity_refreshed_at = :now"
        " FROM jsonb_to_recordset(CAST(:rows AS jsonb))"
        "   AS v(entity_id uuid, score numeric)"
        " WHERE work.entity_id = v.entity_id RETURNING work.entity_id",
        {"rows": payload, "now": now},
    )
    # Anything this run did not touch keeps a stale score, so it is cleared.
    await fetch(
        session,
        "UPDATE work SET popularity = 0, popularity_refreshed_at = :now"
        " WHERE popularity_refreshed_at < :now RETURNING entity_id",
        {"now": now},
    )
    return len(scorable_ids)
