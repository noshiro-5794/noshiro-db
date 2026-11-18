from unittest.mock import AsyncMock

import httpx
import pytest
from mcp.server.auth.provider import AccessToken

from api.mcp import auth, public


@pytest.mark.asyncio
async def test_rate_limit_is_per_subject_and_resets_at_window_boundary(monkeypatch):
    monkeypatch.delenv("REDIS_CACHE_URL", raising=False)
    monkeypatch.delenv("CACHE_URL", raising=False)
    clock = [120]
    monkeypatch.setattr(auth.time, "time", lambda: clock[0])
    limiter = auth.RateLimiter(limit=1, window_seconds=60)
    await limiter.check("one")
    await limiter.check("two")
    with pytest.raises(PermissionError, match="rate limit exceeded"):
        await limiter.check("one")
    clock[0] = 180
    await limiter.check("one")


@pytest.mark.asyncio
async def test_public_http_authentication_tool_contract_and_rate_limit(monkeypatch):
    monkeypatch.delenv("REDIS_CACHE_URL", raising=False)
    monkeypatch.delenv("CACHE_URL", raising=False)
    monkeypatch.setattr(public.settings, "mcp_rate_limit", 1)
    verified = AccessToken(token="valid", client_id="test", subject="1", scopes=["knowledge:read"])

    async def verify(self, token):
        return verified if token == "valid" else None

    monkeypatch.setattr(auth.TokenVerifier, "verify_token", verify)
    search = AsyncMock(return_value={"results": [{"id": "entity"}]})
    monkeypatch.setattr(public.queries, "search_public_entities", search)
    app = public.create_app()
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8010"
        ) as client,
    ):
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        headers = {"Accept": "application/json, text/event-stream"}
        missing = await client.post("/mcp", json=message, headers=headers)
        assert missing.status_code == 401
        invalid = await client.post(
            "/mcp", json=message, headers={**headers, "Authorization": "Bearer invalid"}
        )
        assert invalid.status_code == 401
        headers["Authorization"] = "Bearer valid"
        response = await client.post("/mcp", json=message, headers=headers)
        assert response.status_code == 200, response.text
        assert {tool["name"] for tool in response.json()["result"]["tools"]} == {
            "search_entities",
            "get_entity",
            "get_entity_relations",
        }
        message.update(
            method="tools/call",
            params={"name": "search_entities", "arguments": {"query": "Anime"}},
        )
        response = await client.post("/mcp", json=message, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["result"]["structuredContent"] == {"results": [{"id": "entity"}]}
        response = await client.post("/mcp", json=message, headers=headers)
        assert response.json()["result"]["isError"] is True
        search.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_jwt_is_rejected_without_database_access():
    assert await auth.TokenVerifier().verify_token("invalid") is None
