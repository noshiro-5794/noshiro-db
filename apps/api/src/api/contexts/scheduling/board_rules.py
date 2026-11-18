"""Deterministic provider-priority and broadcast-slot rules for the weekly board."""

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

_WEEKDAY_MAP = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
}


_MINUTE_SOURCE_PRIORITY = {"anilist": 0, "mal": 1, "bangumi": 2}


_WEEKDAY_SOURCE_PRIORITY = {"mal": 0, "anilist": 1, "bangumi": 2}


_DEFAULT_ALLOWED_FORMATS = ("TV", "TV_SHORT", "ONA")


_FORMAT_ALIASES = {
    "TV": "TV",
    "TV_SHORT": "TV_SHORT",
    "ONA": "ONA",
    "WEB": "ONA",
}


_EXTRA_MEDIA_FORMATS = {
    "movie": "MOVIE",
    "ova": "OVA",
    "special": "SPECIAL",
    "tv_special": "SPECIAL",
}


_EXTRA_STATUSES = {"currently_airing", "not_yet_aired", "finished_airing"}


@dataclass(frozen=True, slots=True)
class CandidateBar:
    """One source-supplied bar waiting for canonical deduplication."""

    entity_id: Any
    weekday: int | None
    starts_at: datetime | None = None
    timezone: str = ""
    duration_minutes: int | None = None
    episode_number: int | None = None
    precision: str = "weekday"
    status: str = "tentative"
    provider: str = ""
    format: str = ""
    observation_id: Any = None
    external_id: str = ""


def mal_item_bar(
    *,
    item: dict[str, Any],
    mal_works: dict[int, Any],
    observation_id: Any,
    now: datetime,
    end: datetime,
) -> CandidateBar | None:
    mal_id = item.get("mal_id")
    if not isinstance(mal_id, int) or mal_id not in mal_works:
        return None
    status = str(item.get("status") or "").lower().replace(" ", "_")
    weekday = _WEEKDAY_MAP.get(str(item.get("broadcast_day") or "").strip().lower())
    if weekday is None:
        return mal_extra_bar(
            item=item, entity_id=mal_works[mal_id], observation_id=observation_id, status=status
        )
    is_airing = status == "currently_airing"
    is_upcoming = status == "not_yet_aired"
    if not (is_airing or is_upcoming):
        return None
    raw_time = item.get("broadcast_time")
    timezone_name = str(item.get("timezone") or "Asia/Tokyo")
    starts_at = None
    if is_upcoming:
        starts_at = premiere_occurrence(
            start_date=item.get("start_date"),
            raw_time=raw_time if isinstance(raw_time, str) else "",
            timezone_name=timezone_name,
            now=now,
        )
    elif isinstance(raw_time, str) and ":" in raw_time:
        try:
            hour, minute = raw_time.split(":", 1)
            slot = next_occurrence(
                weekday=weekday,
                hour=int(hour),
                minute=int(minute[:2]),
                timezone_name=timezone_name,
                now=now,
            )
            starts_at = slot
        except ValueError:
            starts_at = None
    if starts_at is not None and (not now <= starts_at < end):
        return None
    entity_id = mal_works[mal_id]
    effective_weekday = starts_at.weekday() + 1 if starts_at is not None else weekday
    return CandidateBar(
        entity_id=entity_id,
        weekday=effective_weekday,
        starts_at=starts_at,
        timezone=timezone_name,
        duration_minutes=as_positive_int(item.get("duration_minutes")),
        precision="minute" if starts_at is not None else "weekday",
        status="scheduled",
        provider="mal",
        format=str(item.get("media_type") or ""),
        observation_id=observation_id,
        external_id=str(mal_id),
    )


def mal_extra_bar(
    *,
    item: dict[str, Any],
    entity_id: Any,
    observation_id: Any,
    status: str,
) -> CandidateBar | None:
    """Build a date-only bar for a film, OVA or special in the season snapshot."""
    format_name = _EXTRA_MEDIA_FORMATS.get(str(item.get("media_type") or "").strip().lower())
    if format_name is None or status not in _EXTRA_STATUSES:
        return None
    start_date = as_date(item.get("start_date"))
    if start_date is None:
        return None
    starts_at = datetime.combine(
        start_date,
        time(hour=0, minute=0),
        tzinfo=ZoneInfo("Asia/Tokyo"),
    ).astimezone(UTC)
    return CandidateBar(
        entity_id=entity_id,
        weekday=None,
        starts_at=starts_at,
        timezone="Asia/Tokyo",
        precision="day",
        status="scheduled",
        provider="mal",
        format=format_name,
        observation_id=observation_id,
        external_id=str(item.get("mal_id") or ""),
    )


def as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def allowed_formats() -> set[str]:
    configured = (
        os.environ.get("CALENDAR_ALLOWED_FORMATS", "").replace(",", " ").split()
        or _DEFAULT_ALLOWED_FORMATS
    )
    return {
        _FORMAT_ALIASES.get(str(value).strip().upper(), str(value).strip().upper())
        for value in configured
    }


def format_allowed(value: Any) -> bool:
    raw = str(value or "").strip().upper()
    if not raw:
        return True  # Unknown formats stay visible rather than silently dropping.
    return _FORMAT_ALIASES.get(raw, raw) in allowed_formats()


def choose_bar(bars: list[CandidateBar]) -> CandidateBar:
    """Pick the fused bar: precise instant first, then provider role."""
    minute_bars = [bar for bar in bars if bar.starts_at is not None]
    if minute_bars:
        return min(
            minute_bars,
            key=lambda bar: (
                _MINUTE_SOURCE_PRIORITY.get(bar.provider, 99),
                bar.starts_at,
            ),
        )
    return min(
        bars,
        key=lambda bar: _WEEKDAY_SOURCE_PRIORITY.get(bar.provider, 99),
    )


def corroborates(chosen: CandidateBar, other: CandidateBar) -> bool:
    if other is chosen or other.provider == chosen.provider:
        return False
    if chosen.starts_at is None or other.starts_at is None:
        return True
    return abs((other.starts_at - chosen.starts_at).total_seconds()) <= 1800


def source_role(*, chosen: CandidateBar, bar: CandidateBar) -> str:
    if bar is chosen:
        if bar.precision == "minute":
            return "precise" if bar.provider == "anilist" else "primary"
        if bar.precision == "day":
            return "date-primary"
        return "weekday-primary"
    if bar.precision == "minute":
        return "corroboration"
    if bar.precision == "day":
        return "date-corroboration"
    return "weekday-corroboration"


def season_start_date(season_key: str) -> date | None:
    value = (season_key or "").strip().upper()
    if len(value) != 6 or value[4] != "Q" or value[-1] not in "1234":
        return None
    try:
        year = int(value[:4])
    except ValueError:
        return None
    quarter = int(value[-1])
    return date(year, 1 + (quarter - 1) * 3, 1)


def next_season_key(season_key: str) -> str:
    value = (season_key or "").strip().upper()
    if len(value) != 6 or value[4] != "Q" or value[-1] not in "1234":
        return value
    year = int(value[:4])
    quarter = int(value[-1])
    return f"{year + 1}Q1" if quarter == 4 else f"{year}Q{quarter + 1}"


def add_months(value: date, months: int) -> date:
    """First day of the month `months` away from `value`."""
    index = value.month - 1 + months
    return date(value.year + index // 12, index % 12 + 1, 1)


def season_switch_date(season_key: str) -> date:
    start = season_start_date(season_key)
    if start is None:
        return datetime.now(
            ZoneInfo(os.environ.get("DEPLOYMENT_TIME_ZONE") or "Asia/Shanghai")
        ).date()
    return start + timedelta(days=int(os.environ.get("SEASON_SWITCH_GRACE_DAYS", "3")))


def season_switch_allowed(season_key: str, *, today: date) -> bool:
    start = season_start_date(season_key)
    if start is None:
        return True
    return today >= season_switch_date(season_key)


def next_occurrence(
    *,
    weekday: int,
    hour: int,
    minute: int,
    timezone_name: str,
    now: datetime,
) -> datetime | None:
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = ZoneInfo("Asia/Tokyo")
    local_now = now.astimezone(zone)
    days_ahead = (weekday - local_now.isoweekday()) % 7
    local_slot = datetime.combine(
        local_now.date() + timedelta(days=days_ahead),
        time(hour=hour, minute=minute),
        tzinfo=zone,
    )
    if local_slot <= local_now:
        local_slot += timedelta(days=7)
    return local_slot.astimezone(UTC)


def premiere_occurrence(
    *,
    start_date: Any,
    raw_time: str,
    timezone_name: str,
    now: datetime,
) -> datetime | None:
    """Return the exact premiere instant for a not-yet-aired MAL entry."""
    if not isinstance(start_date, str) or ":" not in raw_time:
        return None
    try:
        premiere_day = date.fromisoformat(start_date)
        hour, minute = raw_time.split(":", 1)
        premiere_time = time(hour=int(hour), minute=int(minute[:2]))
    except (TypeError, ValueError):
        return None
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = ZoneInfo("Asia/Tokyo")
    premiere = datetime.combine(premiere_day, premiere_time, tzinfo=zone)
    if premiere <= now:
        return None
    return premiere.astimezone(UTC)


def as_positive_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
