"""RFC 9457 problem responses, matching the Django service byte for byte.

The web client reads `detail` and shows it, and the `trace_id` is what makes a
user report actionable. `title` is the HTTP reason phrase, and `instance` is the
request path — the same fields Django emits from its exception handler.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


class ProblemError(Exception):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def problem_payload(
    *, status_code: int, detail: str, instance: str, trace_id: str
) -> dict[str, Any]:
    return {
        "type": "about:blank",
        "title": HTTPStatus(status_code).phrase,
        "status": status_code,
        "detail": detail,
        "instance": instance,
        "trace_id": trace_id,
    }


async def problem_handler(request: Request, error: Exception) -> JSONResponse:
    status_code = getattr(error, "status_code", 500)
    detail = getattr(error, "detail", "Internal Server Error")
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content=problem_payload(
            status_code=status_code,
            detail=detail,
            instance=request.url.path,
            trace_id=uuid4().hex,
        ),
    )
