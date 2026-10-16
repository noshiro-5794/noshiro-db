import uuid
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from integrations.mcp.auth import MCPRateLimiter, NoshiroJWTTokenVerifier
from integrations.mcp.queries import (
    get_public_entity,
    get_public_relations,
    search_public_entities,
)
from integrations.mcp.server import AuthenticatedMCPServer

READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def create_external_mcp_server() -> AuthenticatedMCPServer:
    limiter = MCPRateLimiter(
        limit=settings.MCP_RATE_LIMIT,
        window_seconds=settings.MCP_RATE_WINDOW_SECONDS,
    )
    server = AuthenticatedMCPServer(
        "Noshiro Public Knowledge",
        instructions="Read authenticated public safe knowledge projections only.",
        token_verifier=NoshiroJWTTokenVerifier(),
        required_scopes=["knowledge:read"],
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )

    async def authorize() -> str:
        access_token = get_access_token()
        if access_token is None or access_token.subject is None:
            raise ToolError("Authenticated MCP subject is required.")
        try:
            await sync_to_async(limiter.check, thread_sensitive=False)(
                access_token.subject
            )
        except PermissionError as exc:
            raise ToolError(str(exc)) from exc
        return access_token.subject

    @server.tool(annotations=READ_ONLY, structured_output=True)
    async def search_entities(
        query: str = "",
        collection: str = "",
        language: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search public safe entity projections."""
        await authorize()
        return await sync_to_async(search_public_entities, thread_sensitive=True)(
            query=query,
            collection=collection,
            language=language,
            limit=limit,
        )

    @server.tool(annotations=READ_ONLY, structured_output=True)
    async def get_entity(
        entity_id: uuid.UUID,
        language: str = "",
    ) -> dict[str, Any]:
        """Read one public safe entity projection."""
        await authorize()
        return await sync_to_async(get_public_entity, thread_sensitive=True)(
            entity_id=entity_id,
            language=language,
        )

    @server.tool(annotations=READ_ONLY, structured_output=True)
    async def get_entity_relations(
        entity_id: uuid.UUID,
        language: str = "",
    ) -> dict[str, Any]:
        """Read public relations from one public entity."""
        await authorize()
        return await sync_to_async(get_public_relations, thread_sensitive=True)(
            entity_id=entity_id,
            language=language,
        )

    return server
