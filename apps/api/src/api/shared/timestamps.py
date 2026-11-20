"""ISO 8601 rendering for API and worker payloads."""

from datetime import UTC, date, datetime


def isoformat(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        return value.isoformat()
    rendered = value.astimezone(UTC).isoformat()
    return rendered[:-6] + "Z" if rendered.endswith("+00:00") else rendered
