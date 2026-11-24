"""Commit eligible source responses from provider worker threads."""

import asyncio
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, contextmanager
from threading import get_ident
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.ingestion import archive
from api.integrations.providers.capture import SourceResponse, capture_responses
from api.worker.session import session_scope

type SessionScope = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@contextmanager
def archive_responses(
    scope: SessionScope | None = None, *, batch_id: UUID | None = None
) -> Iterator[None]:
    loop = asyncio.get_running_loop()
    loop_thread = get_ident()
    open_session = scope or session_scope

    async def persist(response: SourceResponse) -> bool:
        async with open_session() as session:
            try:
                await archive.store(session, response, batch_id=batch_id)
            except PermissionError:
                return False
        return True

    def receive(response: SourceResponse) -> bool:
        if get_ident() == loop_thread:
            raise RuntimeError("Archived provider requests must run in a worker thread.")
        return asyncio.run_coroutine_threadsafe(persist(response), loop).result()

    with capture_responses(receive):
        yield


@asynccontextmanager
async def archive_catalogue(
    provider: str, external_id: str, *, scope: SessionScope | None = None
) -> AsyncIterator[None]:
    open_session = scope or session_scope
    async with open_session() as session:
        batch_id = await archive.begin_batch(session, provider, external_id)
    with archive_responses(open_session, batch_id=batch_id):
        yield
    if batch_id is not None:
        async with open_session() as session:
            await archive.complete_batch(session, batch_id)


async def fetch_archived[T, **P](
    scope: SessionScope, action: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    with archive_responses(scope):
        return await asyncio.to_thread(action, *args, **kwargs)
