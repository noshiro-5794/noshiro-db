from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest

from api.contexts.knowledge import retrieval
from api.contexts.presentation.fragments import fetch
from api.worker import mal_import


@pytest.fixture
async def retrieval_runtime(mal_session, monkeypatch):
    @asynccontextmanager
    async def scope():
        yield mal_session

    monkeypatch.setattr(retrieval, "session_scope", scope)
    return mal_session


@pytest.mark.asyncio
async def test_knowledge_tools_return_public_projections_and_hide_private_entities(
    retrieval_runtime,
):
    session = retrieval_runtime
    public = await mal_import.import_anime(session, {"id": 1, "title": "Public Anime"})
    private = await mal_import.import_anime(session, {"id": 2, "title": "Private Anime"})
    await fetch(
        session,
        "UPDATE entity SET visibility='private' WHERE id=:id RETURNING id",
        {"id": private},
    )
    result = await retrieval.TOOLS["knowledge.search_entities"].execute({"query": "Anime"})
    assert [row["id"] for row in result.results] == [str(public)]
    detail = await retrieval.TOOLS["knowledge.get_entity"].execute({"entity_id": str(public)})
    assert detail.entity["id"] == str(public)
    with pytest.raises(LookupError, match="Public entity not found"):
        await retrieval.TOOLS["knowledge.get_entity"].execute({"entity_id": str(private)})


@pytest.mark.asyncio
async def test_mal_tool_preserves_compact_fields_and_storage_policy(retrieval_runtime, monkeypatch):
    session = retrieval_runtime
    await fetch(
        session,
        "UPDATE provider SET storage_policy='forbidden' WHERE slug='mal' RETURNING id",
        {},
    )
    client = Mock()
    client.search_anime.return_value = {
        "data": [
            {"node": {"id": 42, "title": "Anime", "broadcast": {"start_time": "12:00"}}},
            {"node": {"title": "Missing id"}},
            None,
        ]
    }
    monkeypatch.setattr(retrieval, "MALClient", lambda: client)
    result = await retrieval.TOOLS["mal.search_anime"].execute({"query": "Anime", "limit": 3})
    assert len(result.results) == 1
    assert result.results[0]["id"] == 42
    assert result.results[0]["broadcast_time"] == "12:00"
    assert result.results[0]["alternative_titles"] == {"synonyms": [], "en": "", "ja": ""}
    client.forbid_storage.assert_called_once_with(forbidden=True)
    client.search_anime.assert_called_once_with(query="Anime", limit=3)
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_mal_tool_closes_client_when_search_fails(retrieval_runtime, monkeypatch):
    client = Mock()
    client.search_anime.side_effect = RuntimeError("Unavailable")
    monkeypatch.setattr(retrieval, "MALClient", lambda: client)
    with pytest.raises(RuntimeError, match="Unavailable"):
        await retrieval.TOOLS["mal.search_anime"].execute({"query": "Anime"})
    client.close.assert_called_once()
