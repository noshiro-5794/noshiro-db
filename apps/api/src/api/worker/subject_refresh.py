"""Rotating refresh of the Bangumi subjects the catalogue already knows.

Bangumi publishes no "changed since" feed, so the only way to notice that a title or an
episode count moved is to re-fetch records we already hold — oldest first, legacy rows
before the rest, because a legacy row carries no payload and re-fetching it is also what
promotes it onto the modern record/revision/observation form.

Ported from `SubjectRefreshService`. The target selection is the part worth comparing
against the old service before a single request is made: a different ordering means a
different slice of the catalogue gets refreshed, every day, forever.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch
from api.integrations.providers.errors import ProviderError
from api.worker.subject_import import import_subject

TASK_NAME = "bangumi_subject_refresh"
MAX_LIMIT = 20000
LEGACY = "legacy"
ACTIVE = "active"
LISTED = "listed"


async def select_targets(
    session: AsyncSession, *, limit: int, catalogue_only: bool = True
) -> list[Any]:
    """Legacy rows first, then whatever was refreshed longest ago."""
    bounded = max(1, min(int(limit), MAX_LIMIT))
    base = """
        FROM provider_record AS r
        JOIN provider_namespace AS ns ON ns.id = r.namespace_id
        JOIN provider AS p ON p.id = ns.provider_id
        WHERE p.slug = 'bangumi' AND ns.slug = 'subject' AND r.status = :active
        {catalogue}
    """
    catalogue = ""
    if catalogue_only:
        catalogue = """
          AND EXISTS (
            SELECT 1 FROM entity_representation AS rep
            JOIN curated_membership AS m ON m.entity_id = rep.entity_id
            WHERE rep.provider_record_id = r.id AND rep.is_active
              AND m.listing_state = :listed
          )
        """
    order = " ORDER BY r.last_seen_at ASC NULLS FIRST, r.external_id"
    legacy = await fetch(
        session,
        "SELECT r.id, r.external_id, r.raw_state"
        + base.format(catalogue=catalogue)
        + " AND r.raw_state = :legacy"
        + order
        + " LIMIT :limit",
        {"active": ACTIVE, "listed": LISTED, "legacy": LEGACY, "limit": bounded},
    )
    remaining = bounded - len(legacy)
    if remaining <= 0:
        return legacy
    rest = await fetch(
        session,
        "SELECT r.id, r.external_id, r.raw_state"
        + base.format(catalogue=catalogue)
        + " AND r.raw_state <> :legacy"
        + order
        + " LIMIT :limit",
        {"active": ACTIVE, "listed": LISTED, "legacy": LEGACY, "limit": remaining},
    )
    return legacy + rest


async def refresh(
    session: AsyncSession,
    client: Any,
    *,
    limit: int,
    catalogue_only: bool = True,
) -> dict[str, Any]:
    """Re-fetch up to ``limit`` known subjects, legacy rows first."""
    targets = await select_targets(session, limit=limit, catalogue_only=catalogue_only)
    result: dict[str, Any] = {
        "task_name": TASK_NAME,
        "limit": max(1, min(int(limit), MAX_LIMIT)),
        "catalogue_only": catalogue_only,
        "selected": len(targets),
        "legacy_selected": sum(1 for row in targets if row.raw_state == LEGACY),
        "refreshed": 0,
        "promoted": 0,
        "missing": 0,
        "skipped": 0,
        "failed": 0,
    }
    for record in targets:
        try:
            external_id = int(record.external_id)
        except (TypeError, ValueError):
            result["skipped"] += 1
            continue
        try:
            data = await asyncio.to_thread(client.fetch_subject, external_id)
        except ProviderError as error:
            if error.is_not_found:
                # A direct 404 is authoritative: the subject is gone.
                await fetch(
                    session,
                    "UPDATE provider_record SET status = 'missing', updated_at = now()"
                    " WHERE id = :id RETURNING id",
                    {"id": record.id},
                )
                result["missing"] += 1
                continue
            result["failed"] += 1
            continue
        try:
            await import_subject(session, data)
        except Exception:
            result["failed"] += 1
            continue
        result["refreshed"] += 1
        if record.raw_state == LEGACY:
            result["promoted"] += 1
    return result


__all__ = ["MAX_LIMIT", "TASK_NAME", "refresh", "select_targets"]
