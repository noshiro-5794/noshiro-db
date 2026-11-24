import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_internal_mcp_process_initializes_lists_tools_and_validates_arguments():
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "api.mcp.internal"])
    async with (
        stdio_client(parameters) as (reader, writer),
        ClientSession(reader, writer) as client,
    ):
        initialized = await client.initialize()
        assert initialized.server_info.name == "Noshiro Internal Knowledge Harness"
        tools = await client.list_tools()
        assert {tool.name for tool in tools.tools} == {
            "search_entities",
            "get_match_candidate",
            "submit_proposal",
            "get_metadata_evidence",
            "submit_metadata_draft",
        }
        result = await client.call_tool("get_match_candidate", {"candidate_id": "invalid-uuid"})
        assert result.is_error
