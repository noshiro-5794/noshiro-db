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
from typing import Any
from urllib.parse import parse_qs, urlencode

from api.shared.problems import ProblemError

# DRF refuses cursors that ask to skip further than this.
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
        if offset < 0 or offset > OFFSET_CUTOFF:
            raise ValueError("offset")
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
