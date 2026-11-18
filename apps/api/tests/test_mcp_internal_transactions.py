from contextlib import asynccontextmanager
from uuid import UUID

import pytest

from api.contexts.knowledge import retrieval
from api.contexts.matching import submissions
from api.contexts.presentation.fragments import fetch
from api.mcp import queries
from api.mcp.internal import create_server
from api.worker import mal_import


@pytest.fixture
async def mcp_runtime(mal_session, monkeypatch):
    session = mal_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    for module in [submissions, queries, retrieval]:
        monkeypatch.setattr(module, "session_scope", scope)
    left = await mal_import.import_anime(session, {"id": 1, "title": "Anime"})
    right = await mal_import.import_anime(session, {"id": 2, "title": "Other"})
    left, right = sorted((left, right), key=str)
    identifier = (
        await fetch(
            session,
            "INSERT INTO match_candidate (id,left_entity_id,right_entity_id,policy_version,score,"
            "runner_up_margin,status,hard_conflicts,created_at,updated_at) VALUES "
            "(gen_random_uuid(),:left,:right,'mcp-test',0.99,0.1,'pending','[]',now(),now()) "
            "RETURNING id",
            {"left": left, "right": right},
        )
    )[0].id
    await session.commit()
    return session, identifier, create_server()


@pytest.mark.asyncio
async def test_internal_mcp_tool_contract_reads_and_submits_audited_pending_proposal(mcp_runtime):
    session, identifier, server = mcp_runtime
    assert {tool.name for tool in await server.list_tools()} == {
        "search_entities",
        "get_match_candidate",
        "submit_proposal",
    }
    result = await server.call_tool("get_match_candidate", {"candidate_id": str(identifier)})
    assert result.structured_content["id"] == str(identifier)
    result = await server.call_tool(
        "submit_proposal",
        {
            "candidate_id": str(identifier),
            "decision": "bind",
            "confidence": "0.95",
            "reason": "Evidence agrees",
        },
    )
    assert result.structured_content["canonical_write"] is False
    proposal = (await fetch(session, "SELECT status,payload FROM ai_proposal", {}))[0]
    assert proposal.status == "pending" and proposal.payload["confidence"] == "0.95"
    run = (await fetch(session, "SELECT provider,input_metadata,status FROM ai_run", {}))[0]
    assert run.provider == "internal_mcp" and run.status == "succeeded"
    assert run.input_metadata == {"candidate_id": str(identifier), "transport": "stdio"}
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_redirect", {}))[0].n == 0


@pytest.mark.asyncio
async def test_submission_failure_rolls_back_inference_audit(mcp_runtime, monkeypatch):
    session, identifier, _ = mcp_runtime
    real_fetch = submissions.fetch

    async def failed(session, sql, params):
        if sql.startswith("INSERT INTO ai_proposal"):
            raise RuntimeError("Proposal write failed")
        return await real_fetch(session, sql, params)

    monkeypatch.setattr(submissions, "fetch", failed)
    from decimal import Decimal

    with pytest.raises(RuntimeError, match="Proposal write failed"):
        await submissions.submit(
            candidate_id=identifier,
            decision="bind",
            confidence=Decimal("0.95"),
            reason="Evidence agrees",
        )
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_run", {}))[0].n == 0


@pytest.mark.asyncio
async def test_public_detail_preserves_memberships_and_relations_hide_private_targets(mcp_runtime):
    from mcp.server.mcpserver.exceptions import ToolError

    session, identifier, _ = mcp_runtime
    pair = (await fetch(session, "SELECT * FROM match_candidate WHERE id=:id", {"id": identifier}))[
        0
    ]
    detail = await queries.get_public_entity(entity_id=pair.left_entity_id)
    assert detail["memberships"] and detail["memberships"][0]["listing_state"] == "listed"
    assert detail["merged_from"] == [] and detail["is_merged"] is False
    await fetch(
        session,
        "INSERT INTO entity_relation "
        "(from_entity_id,to_entity_id,relation_type,qualifiers,created_at,updated_at) "
        "VALUES (:source,:target,'sequel','{}',now(),now()) RETURNING id",
        {"source": pair.left_entity_id, "target": pair.right_entity_id},
    )
    await session.commit()
    relations = await queries.get_public_relations(entity_id=pair.left_entity_id)
    assert [row["target"]["id"] for row in relations["results"]] == [str(pair.right_entity_id)]
    await fetch(
        session,
        "UPDATE entity SET visibility='private' WHERE id=:id RETURNING id",
        {"id": pair.right_entity_id},
    )
    await session.commit()
    assert await queries.get_public_relations(entity_id=pair.left_entity_id) == {"results": []}
    with pytest.raises(ToolError, match="Public entity not found"):
        await queries.get_public_entity(entity_id=pair.right_entity_id)


@pytest.mark.asyncio
async def test_missing_candidate_creates_no_proposal_or_inference(mcp_runtime):
    session, _, server = mcp_runtime
    from mcp.server.mcpserver.exceptions import ToolError

    with pytest.raises(ToolError, match="Match candidate not found"):
        await server.call_tool(
            "submit_proposal",
            {
                "candidate_id": str(UUID(int=1)),
                "decision": "bind",
                "confidence": "0.95",
                "reason": "Evidence agrees",
            },
        )
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_run", {}))[0].n == 0
