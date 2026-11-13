"""Where a provider's id space currently ends, discovered rather than guessed.

Ported from `apps/sync/providers/frontier.py`. The walk is kept as a pure function so it
can be tested with a fake fetcher: no network, no database, and the stopping rules are
visible in one place.

The rules are the old ones, and they matter:

* ``max_misses`` ids in a row answering "no such record" ends the walk — that is the
  frontier.
* Any other provider failure ends the walk **without** recording a miss: a provider
  rate-limiting us must not look like a provider that ran out of records.
* An outage leaves the recorded frontier exactly as it was; writing it again would only
  dirty the table.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch as sql_fetch

FRONTIER_TASK_NAME = "provider_frontier"
NUMERIC_ID = r"^[0-9]+$"


class ProviderError(Exception):
    """A provider answered, and the answer says the record does not exist."""

    def __init__(self, message: str, *, is_not_found: bool = False) -> None:
        super().__init__(message)
        self.is_not_found = is_not_found


@dataclass(frozen=True)
class Frontier:
    highest_existing_id: int
    probed_to: int
    seed: int

    @property
    def ceiling(self) -> int:
        return max(self.highest_existing_id, self.probed_to, self.seed)


@dataclass(frozen=True)
class ProbeResult:
    highest_existing_id: int
    probed_to: int
    probed: int
    misses: int
    stopped_by: str


def frontier_shard(*, provider_slug: str, namespace_slug: str) -> str:
    return f"{provider_slug}:{namespace_slug}"


def walk(
    fetch: Callable[[int], Any],
    *,
    start: Frontier,
    window: int,
    max_misses: int,
) -> ProbeResult:
    """Walk ids upward until enough in a row do not exist.

    ``fetch`` answers with anything for an id that exists and raises
    :class:`ProviderError` with ``is_not_found`` for one that does not.
    """
    highest = start.highest_existing_id
    probed_to = start.ceiling
    misses = 0
    probed = 0
    stopped_by = "window"
    broke = False
    limit = max(1, window)
    miss_limit = max(1, max_misses)

    while probed < limit and misses < miss_limit:
        candidate = probed_to + 1
        probed += 1
        try:
            fetch(candidate)
        except ProviderError as error:
            if not error.is_not_found:
                stopped_by = "provider_error"
                broke = True
                break
            misses += 1
            probed_to = candidate
            continue
        except Exception:
            stopped_by = "unexpected_error"
            broke = True
            break
        highest = candidate
        probed_to = candidate
        misses = 0

    if not broke:
        stopped_by = "missing_run" if misses >= miss_limit else "window"

    return ProbeResult(
        highest_existing_id=highest,
        probed_to=probed_to,
        probed=probed,
        misses=misses,
        stopped_by=stopped_by,
    )


async def highest_stored_id(
    session: AsyncSession, *, provider_slug: str, namespace_slug: str
) -> int:
    """Highest numeric id this catalogue already holds from that id space."""
    rows = await sql_fetch(
        session,
        """
        SELECT max(CAST(r.external_id AS integer)) AS highest
        FROM provider_record AS r
        JOIN provider_namespace AS ns ON ns.id = r.namespace_id
        JOIN provider AS p ON p.id = ns.provider_id
        WHERE p.slug = :provider AND ns.slug = :namespace
          AND r.external_id ~ :numeric
        """,
        {
            "provider": provider_slug,
            "namespace": namespace_slug,
            "numeric": NUMERIC_ID,
        },
    )
    value = rows[0].highest if rows else None
    return int(value or 0)


async def read_frontier(
    session: AsyncSession, *, provider_slug: str, namespace_slug: str, seed: int
) -> Frontier:
    rows = await sql_fetch(
        session,
        "SELECT end_id, current_id FROM sync_state WHERE task_name = :task"
        " AND shard = :shard",
        {
            "task": FRONTIER_TASK_NAME,
            "shard": frontier_shard(
                provider_slug=provider_slug, namespace_slug=namespace_slug
            ),
        },
    )
    if not rows:
        return Frontier(highest_existing_id=seed, probed_to=seed, seed=seed)
    state = rows[0]
    return Frontier(
        highest_existing_id=state.end_id or seed,
        probed_to=max(state.current_id, state.end_id or 0, seed),
        seed=seed,
    )


async def probe_frontier(
    session: AsyncSession,
    *,
    provider_slug: str,
    namespace_slug: str,
    fetch: Callable[[int], Any],
    seed: int,
    window: int,
    max_misses: int,
    persist: bool = True,
) -> dict[str, Any]:
    start = await read_frontier(
        session, provider_slug=provider_slug, namespace_slug=namespace_slug, seed=seed
    )
    result = await asyncio.to_thread(
        walk, fetch, start=start, window=window, max_misses=max_misses
    )
    if persist and result.probed and (
        result.highest_existing_id,
        result.probed_to,
    ) != (start.highest_existing_id, start.ceiling):
        await sql_fetch(
            session,
            """
            INSERT INTO sync_state (task_name, shard, current_id, end_id, status,
                                    updated_at, fail_count)
            VALUES (:task, :shard, :current, :end, 'finished', now(), 0)
            ON CONFLICT (task_name, shard) DO UPDATE
              SET current_id = EXCLUDED.current_id,
                  end_id = EXCLUDED.end_id,
                  status = EXCLUDED.status,
                  updated_at = now()
            RETURNING id
            """,
            {
                "task": FRONTIER_TASK_NAME,
                "shard": frontier_shard(
                    provider_slug=provider_slug, namespace_slug=namespace_slug
                ),
                "current": result.probed_to,
                "end": result.highest_existing_id,
            },
        )
    return {
        "provider": provider_slug,
        "namespace": namespace_slug,
        "highest_existing_id": result.highest_existing_id,
        "probed_to": result.probed_to,
        "probed": result.probed,
        "misses": result.misses,
        "stopped_by": result.stopped_by,
    }


__all__ = [
    "FRONTIER_TASK_NAME",
    "Frontier",
    "ProbeResult",
    "ProviderError",
    "frontier_shard",
    "highest_stored_id",
    "probe_frontier",
    "read_frontier",
    "walk",
]
