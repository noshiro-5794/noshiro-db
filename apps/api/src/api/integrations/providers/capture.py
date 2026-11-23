"""Capture successful upstream response bodies before decoding."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx


@dataclass(frozen=True, slots=True)
class SourceResponse:
    id: UUID
    provider: str
    endpoint: str
    method: str
    status_code: int
    content_type: str
    fetched_at: datetime
    body: bytes


@dataclass(frozen=True, slots=True)
class SourceOrigin:
    fetch_id: UUID
    pointer: str


class SourceObject(dict[str, Any]):
    """A parsed provider object associated with its capture location."""

    def __init__(self, value: dict[str, Any], origin: SourceOrigin) -> None:
        super().__init__(value)
        self.origin = origin


class SourceArray(list[Any]):
    def __init__(self, value: list[Any], origin: SourceOrigin) -> None:
        super().__init__(value)
        self.origin = origin


_receiver: ContextVar[Callable[[SourceResponse], bool | None] | None] = ContextVar(
    "source_response_receiver", default=None
)


@contextmanager
def capture_responses(receiver: Callable[[SourceResponse], bool | None]) -> Iterator[None]:
    token = _receiver.set(receiver)
    try:
        yield
    finally:
        _receiver.reset(token)


def _with_origin(value: Any, fetch_id: UUID, pointer: str = "") -> Any:
    def child(key: str) -> str:
        return f"{pointer}/{key.replace('~', '~0').replace('/', '~1')}"

    if isinstance(value, list):
        return SourceArray(
            [
                _with_origin(item, fetch_id, f"{pointer}/{index}")
                for index, item in enumerate(value)
            ],
            SourceOrigin(fetch_id, pointer),
        )
    if isinstance(value, dict):
        return SourceObject(
            {key: _with_origin(item, fetch_id, child(key)) for key, item in value.items()},
            SourceOrigin(fetch_id, pointer),
        )
    return value


def origins(value: Any) -> tuple[SourceOrigin, ...]:
    """Return one reference to each upstream response used in a projected payload."""
    result: dict[UUID, SourceOrigin] = {}

    def visit(item: Any) -> None:
        if isinstance(item, (SourceObject, SourceArray)):
            result.setdefault(item.origin.fetch_id, item.origin)
        if isinstance(item, dict):
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return tuple(result.values())


def decode_response(provider: str, response: httpx.Response) -> Any:
    receive = _receiver.get()
    if receive is None:
        return response.json()
    capture = SourceResponse(
        id=uuid4(),
        provider=provider.lower(),
        endpoint=response.request.url.path,
        method=response.request.method,
        status_code=response.status_code,
        content_type=response.headers.get("content-type", ""),
        fetched_at=datetime.now(UTC),
        body=response.content,
    )
    retained = receive(capture)
    data = response.json()
    return _with_origin(data, capture.id) if retained else data
