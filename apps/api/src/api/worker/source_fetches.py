"""Commit eligible source responses from provider worker threads."""

import asyncio
from collections.abc import Callable, Iterator
from contextlib import AbstractAsyncContextManager, contextmanager
from threading import get_ident

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.ingestion import archive
from api.integrations.providers.capture import SourceResponse, capture_responses
from api.worker.session import session_scope

type SessionScope = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@contextmanager
def archive_responses(scope: SessionScope | None = None) -> Iterator[None]:
    loop = asyncio.get_running_loop()
    loop_thread = get_ident()
    open_session = scope or session_scope

    async def persist(response: SourceResponse) -> bool:
        async with open_session() as session:
            try:
                await archive.store(session, response)
            except PermissionError:
                return False
        return True

    def receive(response: SourceResponse) -> bool:
        if get_ident() == loop_thread:
            raise RuntimeError("Archived provider requests must run in a worker thread.")
        return asyncio.run_coroutine_threadsafe(persist(response), loop).result()

    with capture_responses(receive):
        yield


async def fetch_archived[T, **P](
    scope: SessionScope, action: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    with archive_responses(scope):
        return await asyncio.to_thread(action, *args, **kwargs)
