import asyncio
import os
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from api.mcp import auth


@pytest.mark.asyncio
async def test_redis_limit_is_atomic_across_instances_and_expires(monkeypatch):
    url = os.environ.get("NOSHIRO_INTEGRATION_REDIS_URL")
    if not url:
        pytest.skip("dedicated Redis integration URL required")
    monkeypatch.setenv("REDIS_CACHE_URL", url)
    monkeypatch.setattr(auth.time, "time", lambda: 120)
    subject = f"mcp-test-{uuid4()}"
    key = f"mcp-rate:{subject}:2"
    limiters = [auth.RateLimiter(limit=3, window_seconds=60) for _ in range(2)]
    async with Redis.from_url(url) as client:
        try:
            results = await asyncio.gather(
                *(limiters[index % 2].check(subject) for index in range(40)),
                return_exceptions=True,
            )
            assert sum(result is None for result in results) == 3
            assert sum(isinstance(result, PermissionError) for result in results) == 37
            assert 0 < await client.ttl(key) <= 61
            assert int(await client.get(key)) == 40
        finally:
            await client.delete(key)
