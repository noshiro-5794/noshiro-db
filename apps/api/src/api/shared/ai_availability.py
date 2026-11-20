"""Shared cooldown after terminal model-provider account failures."""

from __future__ import annotations

import os

from redis.asyncio import Redis

KEY = "noshiro:ai:openai_compatible:unavailable"


async def provider_available() -> bool:
    url = os.environ.get("REDIS_CACHE_URL", "")
    if not url:
        return True
    async with Redis.from_url(url) as client:
        return not bool(await client.exists(KEY))


async def mark_unavailable(status_code: int) -> None:
    url = os.environ.get("REDIS_CACHE_URL", "")
    if not url:
        return
    ttl = max(1, int(os.environ.get("AI_PROVIDER_BREAKER_TTL_SECONDS", "300")))
    async with Redis.from_url(url) as client:
        await client.set(KEY, str(status_code), ex=ttl)
