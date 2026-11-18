"""Authenticated public MCP tools served through stateless Streamable HTTP."""

from typing import Any
from uuid import UUID

import uvicorn
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware, get_access_token
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from starlette.applications import Starlette
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.types import Receive, Scope, Send

from api.config import settings
from api.mcp import queries
from api.mcp.auth import RateLimiter, TokenVerifier


class HTTPRequireAuth(RequireAuthMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            await super().__call__(scope, receive, send)
        else:
            await self.app(scope, receive, send)


def create_server() -> MCPServer[Any]:
    server: MCPServer[Any] = MCPServer(
        "Noshiro Public Knowledge",
        instructions="Read authenticated public safe knowledge projections only.",
    )
    limiter = RateLimiter(
        limit=settings.mcp_rate_limit, window_seconds=settings.mcp_rate_window_seconds
    )
    read_only = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )

    async def authorize() -> None:
        token = get_access_token()
        if token is None or token.subject is None:
            raise ToolError("Authenticated MCP subject is required.")
        try:
            await limiter.check(token.subject)
        except PermissionError as error:
            raise ToolError(str(error)) from error

    @server.tool(annotations=read_only, structured_output=True)
    async def search_entities(
        query: str = "", collection: str = "", language: str = "", limit: int = 20
    ) -> dict[str, Any]:
        """Search public safe entity projections."""
        await authorize()
        return await queries.search_public_entities(
            query=query, collection=collection, language=language, limit=limit
        )

    @server.tool(annotations=read_only, structured_output=True)
    async def get_entity(entity_id: UUID, language: str = "") -> dict[str, Any]:
        """Read one public safe entity projection."""
        await authorize()
        return await queries.get_public_entity(entity_id=entity_id, language=language)

    @server.tool(annotations=read_only, structured_output=True)
    async def get_entity_relations(entity_id: UUID, language: str = "") -> dict[str, Any]:
        """Read public relations from one public entity."""
        await authorize()
        return await queries.get_public_relations(entity_id=entity_id, language=language)

    return server


def create_app() -> Starlette:
    app = create_server().streamable_http_app(
        host=settings.mcp_host, streamable_http_path="/mcp", stateless_http=True, json_response=True
    )
    app.add_middleware(HTTPRequireAuth, required_scopes=["knowledge:read"])
    app.add_middleware(AuthContextMiddleware)
    app.add_middleware(AuthenticationMiddleware, backend=BearerAuthBackend(TokenVerifier()))
    return app


def main() -> None:
    uvicorn.run(create_app(), host=settings.mcp_host, port=settings.mcp_port)


if __name__ == "__main__":
    main()
