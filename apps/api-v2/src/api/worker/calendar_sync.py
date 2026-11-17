"""Partial calendar board projection using the work identities available to the caller.

The complete task still needs its base-subject import and optional manual-detail phases.
The existing writer keeps board replacement atomic and refuses a payload that produces
no usable events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.worker import calendar as calendar_read
from api.worker import calendar_lookup, calendar_write, ingestion, records

PROVIDER = "bangumi"
SUBJECT_NAMESPACE = "subject"
CALENDAR_NAMESPACE = "calendar"
CALENDAR_EXTERNAL_ID = "weekly"
CALENDAR_SCHEMA = "index.schedule"


class CalendarError(RuntimeError):
    """The payload cannot safely replace the current board."""


def season_key(now: datetime) -> str:
    local = now.astimezone(UTC)
    quarter = (local.month - 1) // 3 + 1
    return f"{local.year}Q{quarter}"


async def apply_calendar(
    session: AsyncSession,
    data: list[Any],
    *,
    now: datetime | None = None,
    subject_importer: Any = None,
) -> dict[str, Any]:
    """Swap the board for this payload, without fetching it.

    An optional ``subject_importer`` projects base work data before identity lookup.
    Its failures are counted so usable calendar items can still be applied. The full
    task's separate relation/episode refresh remains pending.
    """
    moment = now or datetime.now(UTC)
    item_count = calendar_read.count_calendar_items(data)
    if item_count == 0:
        raise CalendarError("Bangumi calendar response did not contain any valid subjects.")
    subject_ids = sorted(calendar_read.ids_from_groups(data))
    imported = 0
    import_failures = 0
    if subject_importer is not None:
        for subject_id in subject_ids:
            try:
                await subject_importer(subject_id)
                imported += 1
            except Exception:
                import_failures += 1
    works = await calendar_lookup.work_entities_for_subjects(session, subject_ids)
    events: list[dict[str, Any]] = []
    for group in data:
        if not isinstance(group, dict):
            continue
        weekday = group.get("weekday")
        weekday = weekday if isinstance(weekday, dict) else {}
        for item in group.get("items") or []:
            if not isinstance(item, dict) or not isinstance(item.get("id"), int):
                continue
            work_id = works.get(item["id"])
            if work_id is None:
                continue
            events.append(calendar_read.build_event(work_id=work_id, weekday=weekday, item=item))
    if not events:
        # Every item was unknown to the catalogue, or the payload was malformed. Keeping
        # the current board is the safe answer; the old service refuses here too.
        raise CalendarError("Calendar refresh produced no valid entries; existing rows were kept.")

    previous = await calendar_lookup.previous_calendar_item_ids(session)
    added, removed = calendar_read.diff_ids(set(subject_ids), previous)
    observation_id = await _record_calendar(session, data, moment)
    metadata = calendar_read.board_metadata(
        fetched_at=moment.isoformat(),
        events=[_Weekday(event) for event in events],
        added_ids=added,
        removed_ids=removed,
    )
    written = await calendar_write.replace_board(
        session,
        season_key=season_key(moment),
        observation_id=observation_id,
        events=events,
        metadata=metadata,
    )
    return {
        "item_count": item_count,
        "events": written["events"],
        "archived": written["archived"],
        "added": len(added),
        "removed": len(removed),
        "observation_id": str(observation_id),
        "subjects_imported": imported,
        "subject_import_failures": import_failures,
    }


class _Weekday:
    """Minimal stand-in so the metadata helper can count weekdays."""

    __slots__ = ("weekday",)

    def __init__(self, event: dict[str, Any]) -> None:
        self.weekday = event.get("weekday")


async def _record_calendar(session: AsyncSession, data: list[Any], moment: datetime) -> Any:
    written = await records.record_payload(
        session,
        provider_slug=PROVIDER,
        namespace_slug=CALENDAR_NAMESPACE,
        resource_type="collection",
        external_id=CALENDAR_EXTERNAL_ID,
        payload={"groups": data},
        schema_version="bangumi-calendar-v1",
        fetched_at=moment,
    )
    return await ingestion.record_observation(
        session,
        provider_record_id=written.record_id,
        mapper="bangumi.calendar",
        mapper_version="calendar-sync-v1",
        normalized_data={"groups": data},
        schema_name=CALENDAR_SCHEMA,
        schema_version="1",
        observed_at=moment,
    )


async def sync_calendar(
    session: AsyncSession,
    client: Any,
    *,
    now: datetime | None = None,
    subject_importer: Any = None,
) -> dict[str, Any]:
    """Fetch the weekly board and apply it."""
    data = client.fetch_calendar()
    if not isinstance(data, list):
        raise CalendarError("Bangumi calendar response must be a list.")
    return await apply_calendar(session, data, now=now, subject_importer=subject_importer)


__all__ = [
    "CALENDAR_EXTERNAL_ID",
    "CALENDAR_NAMESPACE",
    "CALENDAR_SCHEMA",
    "CalendarError",
    "apply_calendar",
    "season_key",
    "sync_calendar",
]
