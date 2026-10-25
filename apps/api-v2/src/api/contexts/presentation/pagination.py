"""Page-number pagination in the shape the Django service returns.

`count`, `next`, `previous`, `results`; sixteen items by default, sixty-four at
most. The links are absolute and therefore host-specific — a shadow comparison
ignores them and keeps the count and the page window.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request

from api.shared.problems import ProblemError

DEFAULT_PAGE_SIZE = 16
MAX_PAGE_SIZE = 64


def page_params(request: Request) -> tuple[int, int]:
    raw_page = request.query_params.get("page")
    page = max(1, int(raw_page)) if raw_page else 1
    raw_size = request.query_params.get("page_size")
    size = int(raw_size) if raw_size else DEFAULT_PAGE_SIZE
    return page, min(max(1, size), MAX_PAGE_SIZE)


def page_payload(
    request: Request,
    *,
    count: int,
    results: list[dict[str, Any]],
    page: int,
    page_size: int,
) -> dict[str, Any]:
    def link(number: int) -> str:
        return str(request.url.include_query_params(page=number, page_size=page_size))

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
    if page > pages:
        raise ProblemError(status_code=404, detail="Invalid page.")
