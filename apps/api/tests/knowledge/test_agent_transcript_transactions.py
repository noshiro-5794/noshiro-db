import hashlib
import json

import pytest

from api.contexts.knowledge import agent_runs, checkpoints, transcript
from api.db import fetch


@pytest.mark.asyncio
async def test_transcript_hash_and_native_tool_messages_round_trip(integration_session):
    session = integration_session
    identifier = await agent_runs.create_run(
        session, title="Agent", scope="transcript", key="1", metadata={}
    )
    await transcript.append(session, run_id=identifier, role="system", content="System")
    await transcript.append(
        session,
        run_id=identifier,
        role="assistant",
        tool_calls=[
            {"id": "call-1", "name": "knowledge.search_entities", "arguments": {"query": "作品"}}
        ],
    )
    await transcript.append(
        session,
        run_id=identifier,
        role="tool",
        name="knowledge.search_entities",
        tool_call_id="call-1",
        content='{"results": []}',
    )
    messages = await transcript.messages(session, identifier)
    assert messages[1]["tool_calls"][0]["function"] == {
        "name": "knowledge.search_entities",
        "arguments": '{"query": "作品"}',
    }
    assert messages[2]["tool_call_id"] == "call-1"
    rows = await fetch(
        session,
        "SELECT * FROM agent_message WHERE run_id=:id ORDER BY sequence",
        {"id": identifier},
    )
    assert [row.sequence for row in rows] == [1, 2, 3]
    for row in rows:
        body = {
            key: getattr(row, key)
            for key in ["role", "content", "name", "tool_call_id", "tool_calls"]
        }
        assert (
            row.content_hash
            == hashlib.sha256(
                json.dumps(
                    body, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")
                ).encode()
            ).hexdigest()
        )
    model = await agent_runs.create_step(
        session, run_id=identifier, skill="", payload={}, kind="model", first_sequence=1
    )
    child = await agent_runs.create_step(
        session,
        run_id=identifier,
        skill="",
        payload={},
        kind="tool",
        parent_id=model,
        first_sequence=1,
    )
    await agent_runs.finish_step(session, child, {"results": []})
    snapshot = await checkpoints.capture(session, identifier)
    assert snapshot["message_count"] == 3 and snapshot["step_count"] == 2
    assert snapshot["last_completed_sequence"] == 2
    assert snapshot["steps"][1]["parent_id"] == str(model)


@pytest.mark.asyncio
async def test_failed_transcript_transaction_preserves_existing_sequence(integration_session):
    session = integration_session
    identifier = await agent_runs.create_run(
        session, title="Agent", scope="transcript", key="2", metadata={}
    )
    await transcript.append(session, run_id=identifier, role="user", content="Original")
    with pytest.raises(RuntimeError):
        async with session.begin_nested():
            await transcript.append(session, run_id=identifier, role="assistant", content="Partial")
            raise RuntimeError("Interrupted write")
    await transcript.append(session, run_id=identifier, role="assistant", content="Complete")
    rows = await fetch(session, "SELECT sequence,content FROM agent_message ORDER BY sequence", {})
    assert [tuple(row) for row in rows] == [(1, "Original"), (2, "Complete")]
