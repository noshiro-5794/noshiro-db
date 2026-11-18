"""Local MCP harness exposing safe projections and auditable proposals."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from api.contexts.knowledge import retrieval
from api.contexts.matching import submissions
from api.mcp import queries


def create_server() -> MCPServer[Any]:
    server: MCPServer[Any] = MCPServer(
        "Noshiro Internal Knowledge Harness",
        instructions="Read source-neutral safe projections and submit auditable proposals.",
    )
    read_only = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )

    @server.tool(annotations=read_only, structured_output=True)
    async def search_entities(
        query: str = "", collection: str = "", language: str = "", limit: int = 20
    ) -> dict[str, Any]:
        """Search public safe entity projections."""
        result = await retrieval.search_entities(
            retrieval.SearchEntitiesInput(
                query=query.strip()[:256],
                collection=collection.strip()[:64],
                language=language[:35],
                limit=max(1, min(limit, 50)),
            )
        )
        return result.model_dump(mode="json")

    @server.tool(annotations=read_only, structured_output=True)
    async def get_match_candidate(candidate_id: UUID) -> dict[str, Any]:
        """Read one match candidate and its safe evidence projection."""
        return await queries.get_match_candidate(candidate_id)

    @server.tool(
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
        structured_output=True,
    )
    async def submit_proposal(
        candidate_id: UUID,
        decision: str,
        confidence: Decimal,
        reason: str,
        prompt_version: str = "internal-mcp-v1",
    ) -> dict[str, Any]:
        """Submit an auditable matching proposal for policy evaluation."""
        try:
            return await submissions.submit(
                candidate_id=candidate_id,
                decision=decision,
                confidence=confidence,
                reason=reason,
                prompt_version=prompt_version,
            )
        except LookupError as error:
            raise ToolError(str(error)) from error

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
