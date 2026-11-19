"""RFC 9457 problem responses, matching the Django service byte for byte.

The web client reads `detail` and shows it, and the `trace_id` is what makes a
user report actionable. `title` is the HTTP reason phrase, and `instance` is the
request path — the same fields Django emits from its exception handler.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ProblemError(Exception):
    """A failure with an optional domain code.

    Django renders domain errors with a type URI and a code (`users.invalid_credentials`);
    plain 404s carry neither. The code is what the web client branches on, so it is
    part of the payload when present and absent otherwise.
    """

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        code: str = "",
        errors: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.errors = errors


def problem_payload(
    *,
    status_code: int,
    detail: str,
    instance: str,
    trace_id: str,
    code: str = "",
    errors: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": f"https://noshiro.moe/problems/{code}" if code else "about:blank",
        "title": HTTPStatus(status_code).phrase,
        "status": status_code,
        "detail": detail,
        "instance": instance,
        "trace_id": trace_id,
    }
    if code:
        payload["code"] = code
    if errors is not None:
        payload["errors"] = errors
    return payload


async def problem_handler(request: Request, error: Exception) -> JSONResponse:
    status_code = getattr(error, "status_code", 500)
    detail = getattr(error, "detail", "Internal Server Error")
    code = getattr(error, "code", "")
    errors = getattr(error, "errors", None)
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content=problem_payload(
            status_code=status_code,
            detail=detail,
            instance=request.url.path + (f"?{request.url.query}" if request.url.query else ""),
            trace_id=uuid4().hex,
            code=code,
            errors=errors,
        ),
    )


async def validation_handler(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, RequestValidationError):
        return await problem_handler(request, error)
    details = error.errors()
    if any(item["type"] == "json_invalid" for item in details):
        try:
            json.loads(error.body)
        except (ValueError, TypeError) as cause:
            return await problem_handler(
                request, ProblemError(status_code=400, detail=f"JSON parse error - {cause}")
            )
    if any(item["loc"][0] == "path" for item in details):
        return await problem_handler(request, ProblemError(status_code=404, detail="Not found."))
    messages = {
        "missing": "This field is required.",
        "int_parsing": "A valid integer is required.",
        "int_type": "A valid integer is required.",
        "bool_parsing": "Must be a valid boolean.",
        "bool_type": "Must be a valid boolean.",
        "string_type": "Not a valid string.",
        "uuid_parsing": "Must be a valid UUID.",
    }
    errors: dict[str, list[str]] = {}
    for item in details:
        field = ".".join(str(value) for value in item["loc"][1:]) or "non_field_errors"
        message = messages.get(item["type"], item["msg"])
        if item["type"] != "missing" and item.get("input") is None:
            message = "This field may not be null."
        errors.setdefault(field, []).append(message)
    return await problem_handler(
        request,
        ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors=errors,
        ),
    )


async def http_error_handler(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, HTTPException):
        return await problem_handler(request, error)
    detail = str(error.detail)
    if error.status_code == 404:
        detail = "Not found."
    elif error.status_code == 405:
        detail = f'Method "{request.method}" not allowed.'
    response = await problem_handler(
        request, ProblemError(status_code=error.status_code, detail=detail)
    )
    response.headers.update(error.headers or {})
    return response
