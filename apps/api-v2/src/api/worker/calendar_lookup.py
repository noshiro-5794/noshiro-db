"""Two lookups the calendar flow needs before it can write anything.

Both are reads, and both are compared against the Django service on the same database
before the task is registered:

* ``work_entities_for_subjects`` — which Bangumi subject ids already have a work entity.
  A calendar item whose subject the catalogue has not imported yet cannot become an
  airing event, and the old service simply skips it.
* ``previous_calendar_item_ids`` — the subject ids recorded by the last calendar
  observation, which is what the added/removed diff is computed against.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

BANGUMI_PROVIDER = "bangumi"
SUBJECT_NAMESPACE = "subject"
CALENDAR_NAMESPACE = "calendar"
CALENDAR_EXTERNAL_ID = "weekly"
CALENDAR_SCHEMA = "index.schedule"


async def work_entities_for_subjects(
    session: AsyncSession, subject_ids: list[int]
) -> dict[int, Any]:
    """Subject id -> work entity id, for the ids the catalogue already holds."""
    if not subject_ids:
        return {}
    rows = await fetch(
        session,
        """
        SELECT DISTINCT r.external_id AS external_id, e.id AS entity_id
        FROM provider_record AS r
        JOIN provider_namespace AS ns ON ns.id = r.namespace_id
        JOIN provider AS p ON p.id = ns.provider_id
        JOIN entity_representation AS rep ON rep.provider_record_id = r.id
        JOIN entity AS e ON e.id = rep.entity_id
        WHERE p.slug = :provider AND ns.slug = :namespace
          AND r.status = 'active' AND rep.is_active
          AND e.lifecycle = 'active'
          AND r.external_id = ANY(:ids)
        """,
        {
            "provider": BANGUMI_PROVIDER,
            "namespace": SUBJECT_NAMESPACE,
            "ids": [str(value) for value in subject_ids],
        },
    )
    out: dict[int, Any] = {}
    for row in rows:
        try:
            out[int(row.external_id)] = row.entity_id
        except (TypeError, ValueError):
            continue
    return out


def ids_from_payload(data: Any) -> set[int]:
    """Subject ids in a stored calendar payload.

    The observation wraps the weekday groups as ``{"groups": [...]}``; a bare list is
    accepted too, because guessing wrong here reports an empty diff and an empty diff
    reads as "nothing changed this week".
    """
    if isinstance(data, str):
        data = json.loads(data)
    groups = data.get("groups") if isinstance(data, dict) else data
    ids: set[int] = set()
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        items = group.get("items") or []
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("id"), int):
                ids.add(item["id"])
    return ids


async def previous_calendar_item_ids(session: AsyncSession) -> set[int]:
    """Subject ids from the payload of the most recent calendar observation."""
    rows = await fetch(
        session,
        """
        SELECT o.normalized_data AS data
        FROM provider_observation AS o
        JOIN provider_record AS r ON r.id = o.provider_record_id
        JOIN provider_namespace AS ns ON ns.id = r.namespace_id
        JOIN provider AS p ON p.id = ns.provider_id
        WHERE p.slug = :provider AND ns.slug = :calendar
          AND r.external_id = :external AND o.schema_name = :schema
        ORDER BY o.observed_at DESC
        LIMIT 1
        """,
        {
            "provider": BANGUMI_PROVIDER,
            "calendar": CALENDAR_NAMESPACE,
            "external": CALENDAR_EXTERNAL_ID,
            "schema": CALENDAR_SCHEMA,
        },
    )
    if not rows:
        return set()
    return ids_from_payload(rows[0].data)


__all__ = [
    "CALENDAR_EXTERNAL_ID",
    "CALENDAR_SCHEMA",
    "ids_from_payload",
    "previous_calendar_item_ids",
    "work_entities_for_subjects",
]
