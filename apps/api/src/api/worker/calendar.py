"""Reading the Bangumi weekly board out of its payload.

Ported as pure functions first, because every one of them has a quiet failure mode: a
weekday that cannot be numbered drops a whole show from the board, and an item without an
integer id is a subject the catalogue cannot reference. Each helper therefore skips what it
cannot trust instead of guessing.
"""

from __future__ import annotations

from typing import Any

WEEKDAY_BY_NAME = {
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
    "sun": 7,
}


def weekday_number(weekday: dict[str, Any]) -> int | None:
    """1-7 for a weekday group, or None when the payload does not say."""
    value = weekday.get("id")
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 7:
        return value
    name = str(weekday.get("en") or "").strip().lower()[:3]
    return WEEKDAY_BY_NAME.get(name)


def weekday_raw_value(weekday: dict[str, Any]) -> str:
    """The first non-empty weekday label, in the payload's own order."""
    for key in ("en", "ja", "cn"):
        value = weekday.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:256]
    return ""


def watching_count(item: dict[str, Any]) -> int | None:
    """Read the numeric signal for internal ranking."""
    collection = item.get("collection")
    if not isinstance(collection, dict):
        return None
    doing = collection.get("doing")
    return doing if isinstance(doing, int) and not isinstance(doing, bool) and doing >= 0 else None


def calendar_items(data: list[Any]) -> list[dict[str, Any]]:
    """Every group's usable items, flattened, keeping only integer ids."""
    items: list[dict[str, Any]] = []
    for group in data:
        if not isinstance(group, dict):
            continue
        group_items = group.get("items") or []
        if not isinstance(group_items, list):
            continue
        items.extend(
            item
            for item in group_items
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        )
    return items


def count_calendar_items(data: list[Any]) -> int:
    return len(calendar_items(data))


def ids_from_groups(data: list[Any]) -> set[int]:
    return {item["id"] for item in calendar_items(data)}


def weekday_counts(events: list[Any]) -> dict[str, int]:
    """Airing events per weekday, keyed by string like the API payload it feeds."""
    counts: dict[int, int] = {}
    for event in events:
        weekday = getattr(event, "weekday", None)
        if weekday is None:
            continue
        counts[weekday] = counts.get(weekday, 0) + 1
    return {str(weekday): count for weekday, count in sorted(counts.items())}


__all__ = [
    "WEEKDAY_BY_NAME",
    "board_metadata",
    "build_event",
    "calendar_items",
    "count_calendar_items",
    "diff_ids",
    "ids_from_groups",
    "watching_count",
    "weekday_counts",
    "weekday_number",
    "weekday_raw_value",
]


def build_event(*, work_id: Any, weekday: dict[str, Any]) -> dict[str, Any]:
    """One airing event from a calendar item, matching the old construction.

    ``precision`` degrades to ``unknown`` when the weekday cannot be numbered, rather
    than dropping the show: an entry with an unreadable slot is still airing.
    """
    number = weekday_number(weekday)
    return {
        "work_id": work_id,
        "weekday": number,
        "precision": "weekday" if number is not None else "unknown",
        "raw_value": weekday_raw_value(weekday),
    }


def diff_ids(fetched: set[int], previous: set[int]) -> tuple[list[int], list[int]]:
    """What the new board adds and what it drops, sorted for a stable payload."""
    return sorted(fetched - previous), sorted(previous - fetched)


def board_metadata(
    *,
    fetched_at: str,
    events: list[Any],
    added_ids: list[int],
    removed_ids: list[int],
) -> dict[str, Any]:
    return {
        "fetched_at": fetched_at,
        "weekday_counts": weekday_counts(events),
        "added_ids": added_ids,
        "removed_ids": removed_ids,
    }
