import asyncio
import os
from hashlib import sha256
from ipaddress import IPv6Address
from uuid import uuid4

import httpx
import pytest
from redis.asyncio import Redis

from api.config import settings
from api.main import create_app


@pytest.mark.asyncio
async def test_login_limit_is_shared_by_authentication_paths_and_processes(monkeypatch):
    url = os.environ.get("NOSHIRO_INTEGRATION_REDIS_URL")
    if not url:
        pytest.skip("dedicated Redis integration URL required")
    monkeypatch.setattr(settings, "redis_cache_url", url)
    host = str(IPv6Address(uuid4().int))
    key = f"noshiro:auth-rate:login:{sha256(host.encode()).hexdigest()}"
    first = httpx.ASGITransport(app=create_app(), client=(host, 1000))
    second = httpx.ASGITransport(app=create_app(), client=(host, 1001))
    password_path = "/api/v1/auth/sessions/password/"
    code_path = "/api/v1/auth/sessions/code/"
    async with Redis.from_url(url) as cache:
        try:
            async with (
                httpx.AsyncClient(transport=first, base_url="http://test") as password,
                httpx.AsyncClient(transport=second, base_url="http://test") as code,
            ):
                results = await asyncio.gather(
                    *(password.post(password_path, json={}) for _ in range(8)),
                    *(code.post(code_path, json={}) for _ in range(8)),
                )
                assert sum(result.status_code == 400 for result in results) == 10
                limited = [result for result in results if result.status_code == 429]
                assert len(limited) == 6
                for response in limited:
                    assert response.headers["content-type"] == "application/problem+json"
                    assert 0 < int(response.headers["Retry-After"]) <= 60
                    assert response.json()["status"] == 429
                assert (await code.get("/api/v1/auth/social/github/start/")).status_code == 429
                assert (await code.post("/api/v1/auth/sessions/refresh/")).status_code == 401
            assert await cache.zcard(key) == 10
            assert 0 < await cache.ttl(key) <= 60
        finally:
            await cache.delete(key, key.replace(":login:", ":refresh:"))
