"""Page-number pagination in the shape the Django service returns.

Responses include count, navigation links and results. Page sizes default to sixteen
and cap at sixty-four. Links retain the original filters and page-size spelling.
"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from fastapi import Request
from pydantic import BeforeValidator, Field

from api.shared.cursor import Cursor, encode
from api.shared.problems import ProblemError

DEFAULT_PAGE_SIZE = 16
MAX_PAGE_SIZE = 64
LAST_PAGE = 0


def page_size_value(value: Any, *, default: int = DEFAULT_PAGE_SIZE) -> int:
    try:
        size = int(value)
    except (ValueError, TypeError, OverflowError):
        return default
    return min(size, MAX_PAGE_SIZE) if size > 0 else default


PageSize = Annotated[int, BeforeValidator(page_size_value), Field(ge=1, le=MAX_PAGE_SIZE)]


def _query_link(request: Request, key: str, value: str | None) -> str:
    parts = urlsplit(str(request.url))
    query = parse_qs(parts.query, keep_blank_values=True)
    if value is None:
        query.pop(key, None)
    else:
        query[key] = [value]
    return urlunsplit(parts._replace(query=urlencode(sorted(query.items()), doseq=True)))


def cursor_payload(
    request: Request,
    *,
    results: list[dict[str, Any]],
    next_cursor: Cursor | None,
    previous_cursor: Cursor | None,
) -> dict[str, Any]:
    def link(cursor: Cursor | None) -> str | None:
        if cursor is None:
            return None
        return _query_link(request, "cursor", encode(cursor))

    return {"next": link(next_cursor), "previous": link(previous_cursor), "results": results}


def page_params(request: Request, *, default: int = DEFAULT_PAGE_SIZE) -> tuple[int, int]:
    raw_page = request.query_params.get("page") or "1"
    if raw_page == "last":
        return LAST_PAGE, page_size_value(request.query_params.get("page_size"), default=default)
    try:
        page = int(raw_page)
        if page < 1:
            raise ValueError("page")
    except ValueError as error:
        raise ProblemError(status_code=404, detail="Invalid page.") from error
    return page, page_size_value(request.query_params.get("page_size"), default=default)


def page_number(page: int, page_size: int, count: int) -> int:
    """Resolve the last-page marker using the same count as the selected window."""
    return max(1, (count + page_size - 1) // page_size) if page == LAST_PAGE else page


def page_offset(page: int, page_size: int, count: int) -> int:
    ensure_page(page, page_size, count)
    return (page_number(page, page_size, count) - 1) * page_size


def page_payload(
    request: Request,
    *,
    count: int,
    results: list[dict[str, Any]],
    page: int,
    page_size: int,
) -> dict[str, Any]:
    page = page_number(page, page_size, count)

    def link(number: int) -> str:
        return _query_link(request, "page", str(number) if number != 1 else None)

    has_next = page * page_size < count
    return {
        "count": count,
        "next": link(page + 1) if has_next else None,
        "previous": link(page - 1) if page > 1 else None,
        "results": results,
    }


def ensure_page(page: int, page_size: int, count: int) -> None:
    """A page past the last one is a 404, as DRF's paginator decides."""
    pages = max(1, (count + page_size - 1) // page_size)
    if not 1 <= page_number(page, page_size, count) <= pages:
        raise ProblemError(status_code=404, detail="Invalid page.")
