"""Access-token verification and atomic fixed-window MCP request limits."""

import os
import time

from mcp.server.auth.provider import AccessToken
from redis.asyncio import Redis

from api.config import settings
from api.contexts.access.security import session_claims
from api.contexts.presentation.fragments import fetch
from api.worker.session import session_scope


class TokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        claims = session_claims(token, settings.jwt_secret)
        if claims is None:
            return None
        user_id = int(claims["user_id"])
        async with session_scope() as session:
            active = await fetch(
                session, 'SELECT id FROM "user" WHERE id=:id AND is_active', {"id": user_id}
            )
        if not active:
            return None
        return AccessToken(
            token=token,
            client_id=f"noshiro-user-{user_id}",
            scopes=["knowledge:read"],
            expires_at=int(claims["exp"]),
            subject=str(user_id),
            claims={"token_type": "access"},
        )


class RateLimiter:
    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._window = -1
        self._counts: dict[str, int] = {}

    async def check(self, subject: str) -> None:
        window = int(time.time()) // self.window_seconds
        url = os.environ.get("REDIS_CACHE_URL") or os.environ.get("CACHE_URL", "")
        if url.startswith(("redis://", "rediss://", "unix://")):
            async with Redis.from_url(
                url,
                socket_timeout=float(os.environ.get("CACHE_SOCKET_TIMEOUT", "5")),
                socket_connect_timeout=float(os.environ.get("CACHE_SOCKET_CONNECT_TIMEOUT", "5")),
            ) as client:
                count = int(
                    await client.eval(
                        "local n=redis.call('INCR',KEYS[1]); "
                        "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
                        1,
                        f"mcp-rate:{subject}:{window}",
                        self.window_seconds + 1,
                    )
                )
        else:
            if self._window != window:
                self._counts.clear()
                self._window = window
            count = self._counts.get(subject, 0) + 1
            self._counts[subject] = count
        if count > self.limit:
            raise PermissionError("MCP request rate limit exceeded.")
