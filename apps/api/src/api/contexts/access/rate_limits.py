"""Per-client authentication limits shared by all API processes."""

from hashlib import sha256
from typing import Any, Literal, TypedDict
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.params import Depends as Dependency
from redis.asyncio import Redis
from redis.exceptions import RedisError

from api.config import settings

type Scope = Literal["login", "refresh", "registration", "reset", "verification"]

LIMITS: dict[Scope, tuple[int, int]] = {
    "login": (10, 60),
    "refresh": (30, 60),
    "registration": (5, 3600),
    "reset": (5, 3600),
    "verification": (5, 60),
}
SLIDING_WINDOW = """
local key = KEYS[1]
local duration = tonumber(ARGV[2])
local time = redis.call('TIME')
local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - duration)
if redis.call('ZCARD', key) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    return math.max(1, math.ceil((tonumber(oldest[2]) + duration - now) / 1000))
end
redis.call('ZADD', key, now, ARGV[3])
redis.call('PEXPIRE', key, duration)
return 0
"""
RATE_LIMIT_RESPONSE = {
    "description": "Authentication rate limit exceeded.",
    "headers": {
        "Retry-After": {
            "description": "Seconds until another attempt can be made.",
            "schema": {"type": "integer", "minimum": 1},
        }
    },
    "content": {
        "application/problem+json": {"schema": {"$ref": "#/components/schemas/ProblemDocument"}}
    },
}


class RateLimitOptions(TypedDict):
    dependencies: list[Dependency]
    responses: dict[int | str, dict[str, Any]]


def limited(scope: Scope) -> RateLimitOptions:
    limit, seconds = LIMITS[scope]

    async def enforce(request: Request) -> None:
        if not settings.redis_cache_url:
            return
        host = request.client.host if request.client else "unknown"
        identity = sha256(host.encode()).hexdigest()
        try:
            async with Redis.from_url(
                settings.redis_cache_url, socket_timeout=3, socket_connect_timeout=3
            ) as cache:
                wait = int(
                    await cache.eval(
                        SLIDING_WINDOW,
                        1,
                        f"noshiro:auth-rate:{scope}:{identity}",
                        limit,
                        seconds * 1000,
                        uuid4().hex,
                    )
                )
        except RedisError as error:
            raise HTTPException(503, "Authentication is temporarily unavailable.") from error
        if wait:
            unit = "second" if wait == 1 else "seconds"
            raise HTTPException(
                429,
                f"Request was throttled. Expected available in {wait} {unit}.",
                headers={"Retry-After": str(wait)},
            )

    return {
        "dependencies": [Depends(enforce)],
        "responses": {429: RATE_LIMIT_RESPONSE},
    }
