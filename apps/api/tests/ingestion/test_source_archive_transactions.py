import json
from contextlib import asynccontextmanager

import httpx
import pytest

from api.contexts.ingestion import archive, records
from api.db import fetch
from api.integrations.providers.bangumi import BangumiClient
from api.integrations.providers.capture import capture_responses
from api.integrations.providers.errors import ProviderError
from api.worker import source_fetches
from api.worker.subject_import import import_subject, replay_subject


@pytest.mark.asyncio
async def test_archive_preserves_body_and_replays_latest_revision(bangumi_session):
    session = bangumi_session
    body = b'{ "type": 2, "name": "Source", "id": 5 }\n'
    captured = []
    with capture_responses(captured.append):
        client = BangumiClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body))
        )
        try:
            assert client.fetch_subject(5) == json.loads(body)
        finally:
            client.close()
    document = captured[0]
    assert document.endpoint == "/v0/subjects/5"
    assert document.body == body
    response_id = await archive.store(session, document)
    entity = await replay_subject(session, 5, response_id)
    assert await replay_subject(session, 5, response_id) == entity
    links = await fetch(session, "SELECT fetch_id FROM ingest.revision_source", {})
    assert [row.fetch_id for row in links] == [response_id]

    await import_subject(session, {"id": 5, "name": "Edited", "type": 2})
    with pytest.raises(ValueError, match="newer source revision"):
        await replay_subject(session, 5, response_id)


def test_invalid_json_is_captured_before_decode():
    captured = []
    with capture_responses(captured.append):
        client = BangumiClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"{"))
        )
        try:
            with pytest.raises(ProviderError, match="invalid JSON"):
                client.fetch_subject(5)
        finally:
            client.close()
    assert [document.body for document in captured] == [b"{"]


@pytest.mark.asyncio
async def test_projected_child_keeps_its_pointer_into_the_response(bangumi_session):
    session = bangumi_session

    @asynccontextmanager
    async def local_scope():
        yield session

    body = b'{ "data": [{ "id": 8, "name": "Episode" }], "total": 1 }\n'
    client = BangumiClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    )
    try:
        page = await source_fetches.fetch_archived(
            local_scope, client.fetch_subject_episodes, subject_id=1, limit=100, offset=0
        )
    finally:
        client.close()
    result = await records.record_payload(
        session,
        provider_slug="bangumi",
        namespace_slug="episode",
        resource_type="episode",
        external_id="8",
        payload=page["data"][0],
    )
    rows = await fetch(
        session,
        """
        SELECT link.json_pointer, document.body FROM ingest.revision_source AS link
        JOIN ingest.source_fetch AS source ON source.id = link.fetch_id
        JOIN ingest.source_document AS document ON document.id = source.document_id
        WHERE link.revision_id = :id
        """,
        {"id": result.revision_id},
    )
    assert [tuple(row) for row in rows] == [("/data/0", body)]
