"""Capture successful upstream response bodies before decoding."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
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


_receiver: ContextVar[Callable[[SourceResponse], None] | None] = ContextVar(
    "source_response_receiver", default=None
)


@contextmanager
def capture_responses(receiver: Callable[[SourceResponse], None]) -> Iterator[None]:
    token = _receiver.set(receiver)
    try:
        yield
    finally:
        _receiver.reset(token)


def capture_response(provider: str, response: httpx.Response) -> None:
    if (receive := _receiver.get()) is not None:
        receive(
            SourceResponse(
                id=uuid4(),
                provider=provider.lower(),
                endpoint=response.request.url.path,
                method=response.request.method,
                status_code=response.status_code,
                content_type=response.headers.get("content-type", ""),
                fetched_at=datetime.now(UTC),
                body=response.content,
            )
        )
