"""The timeline cursor, byte for byte the one the Django service issues.

A cursor is base64 of a query string carrying an offset, a direction and a
position. The position is the ordering field of the last row — for the timelines
that is `created_at` as a string — and the offset disambiguates rows that share a
timestamp. Reproducing it matters: a `next` link minted by the old service has to
resume here, and a keyset design would answer the first page correctly and drift
on the second.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode

from api.shared.problems import ProblemError

# DRF caps offsets at this boundary.
OFFSET_CUTOFF = 1000
INVALID = "Invalid cursor."


@dataclass(frozen=True, slots=True)
class Cursor:
    offset: int = 0
    reverse: bool = False
    position: str | None = None


def decode(raw: str | None) -> Cursor:
    if raw is None:
        return Cursor()
    try:
        tokens = parse_qs(
            base64.b64decode(raw.encode("ascii")).decode("ascii"),
            keep_blank_values=True,
        )
        offset = int(tokens.get("o", ["0"])[0])
        if offset < 0:
            raise ValueError("offset")
        offset = min(offset, OFFSET_CUTOFF)
        reverse = bool(int(tokens.get("r", ["0"])[0]))
        position = tokens.get("p", [None])[0]
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ProblemError(status_code=404, detail=INVALID) from error
    return Cursor(offset=offset, reverse=reverse, position=position)


def encode(cursor: Cursor) -> str:
    tokens: dict[str, str] = {}
    if cursor.offset:
        tokens["o"] = str(cursor.offset)
    if cursor.reverse:
        tokens["r"] = "1"
    if cursor.position is not None:
        tokens["p"] = cursor.position
    return base64.b64encode(urlencode(tokens, doseq=True).encode("ascii")).decode("ascii")


def position_of(row: Any, field: str = "created_at") -> str:
    """DRF's position is `str()` of the ordering field, not a serialised value."""
    value = row[field] if isinstance(row, dict) else getattr(row, field)
    return str(value)


def timestamp_position(position: str) -> datetime:
    """Validate a timeline position and bind the timestamp type asyncpg requires."""
    try:
        value = datetime.fromisoformat(position)
    except ValueError as error:
        raise ProblemError(status_code=404, detail=INVALID) from error
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def paginate[Item](
    rows: list[Item], cursor: Cursor, page_size: int
) -> tuple[list[Item], Cursor | None, Cursor | None]:
    """Build both DRF-compatible boundaries from a directional query and its extra row."""
    page = rows[:page_size]
    following = position_of(rows[-1]) if len(rows) > page_size else None
    if cursor.reverse:
        page.reverse()
    has_current = cursor.position is not None or cursor.offset > 0
    has_next = has_current if cursor.reverse else following is not None
    has_previous = following is not None if cursor.reverse else has_current
    next_position = cursor.position if cursor.reverse else following
    previous_position = following if cursor.reverse else cursor.position

    def boundary(*, reverse: bool) -> Cursor | None:
        if not (has_previous if reverse else has_next):
            return None
        position = previous_position if reverse else next_position
        compare = position
        if page and cursor.reverse != reverse and cursor.offset:
            compare = position_of(page[0] if reverse else page[-1])
        offset = 0
        for item in page if reverse else reversed(page):
            position = position_of(item)
            if position != compare:
                break
            compare = position
            offset += 1
        else:
            if page:
                if not (has_next if reverse else has_previous):
                    offset, position = page_size, None
                else:
                    offset = cursor.offset + page_size if cursor.reverse == reverse else 0
                    position = next_position if reverse else previous_position
        return Cursor(offset, reverse, position)

    return page, boundary(reverse=False), boundary(reverse=True)
