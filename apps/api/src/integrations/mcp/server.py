from typing import Any

from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import (
    BearerAuthBackend,
    RequireAuthMiddleware,
)
from mcp.server.auth.provider import TokenVerifier
from mcp.server.mcpserver import MCPServer
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


class _HTTPRequireAuthMiddleware(RequireAuthMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


class AuthenticatedMCPServer(MCPServer):
    """MCPServer whose Streamable HTTP app requires a bearer token.

    MCPServer 2.x moved transport configuration off the constructor, so the
    transport keywords live here and are applied both when the ASGI app is built
    directly and when ``run_streamable_http()`` starts uvicorn. ``host`` keeps
    DNS-rebinding protection scoped to ``MCP_HOST``; ``port`` only exists for
    uvicorn, because the app factories bind wherever the outer server does.
    """

    def __init__(
        self,
        *args: Any,
        token_verifier: TokenVerifier,
        required_scopes: list[str],
        streamable_http_path: str,
        json_response: bool,
        stateless_http: bool,
        host: str,
        port: int,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._noshiro_token_verifier = token_verifier
        self._noshiro_required_scopes = required_scopes
        self._noshiro_host = host
        self._noshiro_port = port
        self._noshiro_streamable_http_kwargs: dict[str, Any] = {
            "streamable_http_path": streamable_http_path,
            "json_response": json_response,
            "stateless_http": stateless_http,
        }

    def _streamable_http_options(self, **overrides: Any) -> dict[str, Any]:
        return {
            "host": self._noshiro_host,
            **self._noshiro_streamable_http_kwargs,
            **overrides,
        }

    def run_streamable_http(self, **kwargs: Any) -> None:
        self.run(
            transport="streamable-http",
            port=self._noshiro_port,
            **self._streamable_http_options(**kwargs),
        )

    def streamable_http_app(self, **kwargs: Any) -> ASGIApp:
        app = super().streamable_http_app(**self._streamable_http_options(**kwargs))
        protected_app = _HTTPRequireAuthMiddleware(
            app,
            required_scopes=self._noshiro_required_scopes,
        )
        auth_context_app = AuthContextMiddleware(protected_app)
        return AuthenticationMiddleware(
            auth_context_app,
            backend=BearerAuthBackend(self._noshiro_token_verifier),
        )
