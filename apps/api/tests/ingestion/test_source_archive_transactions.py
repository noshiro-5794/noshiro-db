import json

import httpx
import pytest

from api.contexts.ingestion import archive
from api.db import fetch
from api.integrations.providers.bangumi import BangumiClient
from api.integrations.providers.capture import capture_responses
from api.integrations.providers.errors import ProviderError
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
