from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

from api.contexts.knowledge import agent_loop, agent_runs, retrieval
from api.contexts.presentation.fragments import fetch
from api.shared import inference
from api.shared.ai import AgentCompletion, AgentToolCall, AIError
from api.worker import provider_search


class FinalOutput(BaseModel):
    decision: str
    mal_id: int | None = None
    confidence: float = 0
    reason: str = ""


def completion(content="", calls=None):
    return AgentCompletion(
        content, "fast-model", {"input_tokens": 12, "output_tokens": 8}, calls or []
    )


@pytest.fixture
async def loop_runtime(mal_session, monkeypatch):
    session = mal_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    for module in [agent_loop, retrieval, inference, provider_search]:
        monkeypatch.setattr(module, "session_scope", scope)
    identifier = await agent_runs.create_run(
        session,
        title="Recall",
        scope="agent-loop-test",
        key="1",
        kind="admin_enrich",
        metadata={"scopes": ["knowledge:read", "mal:read"]},
    )
    await session.commit()
    model = AsyncMock(
        side_effect=[
            completion(calls=[AgentToolCall("call-1", "mal.search_anime", {"query": "Anime"})]),
            completion(
                '{"decision":"found","mal_id":42,"confidence":0.95,"reason":"Source matches"}'
            ),
        ]
    )
    monkeypatch.setattr(agent_loop, "complete_agent", model)
    monkeypatch.setattr(agent_loop.asyncio, "sleep", AsyncMock())
    client = Mock()
    client.search_anime.return_value = {
        "data": [{"node": {"id": 42, "title": "Anime", "media_type": "tv"}}]
    }
    monkeypatch.setattr(retrieval, "MALClient", lambda: client)
    return session, identifier, model, client


async def execute(identifier, **kwargs):
    return await agent_loop.run(
        identifier,
        system_prompt="System",
        user_prompt="Find anime",
        tool_names=["knowledge.search_entities", "knowledge.get_entity", "mal.search_anime"],
        output_model=FinalOutput,
        use_case="mal_recall",
        **kwargs,
    )


@pytest.mark.asyncio
async def test_native_tool_turn_preserves_transcript_budget_checkpoint_and_replay(loop_runtime):
    session, identifier, model, client = loop_runtime
    result = await execute(identifier)
    assert result.status == "succeeded", result.error
    assert result.output["mal_id"] == 42
    rows = await fetch(session, "SELECT role,sequence FROM agent_message ORDER BY sequence", {})
    assert [row.role for row in rows] == ["system", "user", "assistant", "tool", "assistant"]
    run = (await fetch(session, "SELECT budget,checkpoint FROM agent_run", {}))[0]
    assert run.budget["steps_used"] == 3 and run.budget["input_tokens_used"] == 24
    assert run.checkpoint["step_count"] == 3 and run.checkpoint["message_count"] == 5
    assert run.checkpoint["run_status"] == "succeeded"
    assert (await fetch(session, "SELECT count(*) AS n FROM source_artifact", {}))[0].n == 1
    assert (await fetch(session, "SELECT status FROM tool_invocation", {}))[0].status == "succeeded"
    again = await execute(identifier)
    assert again == result and model.await_count == 2
    client.search_anime.assert_called_once()
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_resume_reuses_completed_tool_after_crash_before_transcript_append(loop_runtime):
    session, identifier, model, client = loop_runtime
    calls = [
        AgentToolCall("call-1", "mal.search_anime", {"query": "Anime"}),
        AgentToolCall("call-2", "mal.search_anime", {"query": "Other"}),
    ]
    model.side_effect = [completion(calls=calls), completion('{"decision":"not_found"}')]
    execution = await agent_loop.claim(identifier, resume=False)
    await agent_loop.initialize(execution, "System", "Find anime")
    parent, _, _ = await agent_loop.model_turn(execution, use_case="mal_recall", tools=[])
    await agent_loop.tool_result(execution, calls[0], parent, {"mal.search_anime"})
    await fetch(
        session,
        "UPDATE agent_run SET status='paused',updated_at=clock_timestamp() RETURNING id",
        {},
    )
    await session.commit()
    result = await execute(identifier, resume=True)
    assert result.status == "succeeded", result.error
    assert client.search_anime.call_count == 2
    assert model.await_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM tool_invocation", {}))[0].n == 2
    assert (await fetch(session, "SELECT budget FROM agent_run", {}))[0].budget["steps_used"] == 4
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_message", {}))[0].n == 6


@pytest.mark.asyncio
async def test_budget_is_enforced_before_requested_tools(loop_runtime):
    session, identifier, _, client = loop_runtime
    await fetch(
        session,
        "UPDATE agent_run SET budget=jsonb_build_object('max_steps',1) WHERE id=:id RETURNING id",
        {"id": identifier},
    )
    await session.commit()
    result = await execute(identifier)
    assert result.status == "failed" and "step_budget_exhausted" in result.error
    client.search_anime.assert_not_called()
    assert (await fetch(session, "SELECT checkpoint FROM agent_run", {}))[0].checkpoint[
        "run_status"
    ] == "failed"


@pytest.mark.asyncio
async def test_unlisted_tool_is_returned_as_an_error_to_the_model(loop_runtime):
    session, identifier, model, client = loop_runtime
    model.side_effect = [
        completion(calls=[AgentToolCall("bad", "users.change_settings", {})]),
        completion('{"decision":"not_found"}'),
    ]
    result = await execute(identifier)
    assert result.status == "succeeded"
    content = (await fetch(session, "SELECT content FROM agent_message WHERE role='tool'", {}))[
        0
    ].content
    assert "not allowed" in content
    client.search_anime.assert_not_called()
    assert (await fetch(session, "SELECT count(*) AS n FROM tool_invocation", {}))[0].n == 0


@pytest.mark.asyncio
async def test_invalid_tool_parameters_are_audited_and_can_be_corrected(loop_runtime):
    session, identifier, model, client = loop_runtime
    model.side_effect = [
        completion(calls=[AgentToolCall("bad", "mal.search_anime", {})]),
        completion(calls=[AgentToolCall("good", "mal.search_anime", {"query": "Anime"})]),
        completion('{"decision":"found","mal_id":42}'),
    ]
    result = await execute(identifier)
    assert result.status == "succeeded", result.error
    rows = await fetch(session, "SELECT status FROM tool_invocation ORDER BY created_at", {})
    assert [row.status for row in rows] == ["failed", "succeeded"]
    client.search_anime.assert_called_once()


@pytest.mark.asyncio
async def test_transient_model_errors_retry_and_charge_attempts(loop_runtime):
    session, identifier, model, _ = loop_runtime
    model.side_effect = [
        AIError("Temporary", retryable=True),
        completion('{"decision":"not_found"}'),
    ]
    result = await execute(identifier)
    assert result.status == "succeeded", result.error
    assert model.await_count == 2
    assert (await fetch(session, "SELECT budget FROM agent_run", {}))[0].budget["steps_used"] == 2
    step = (await fetch(session, "SELECT retry_count,status FROM agent_step", {}))[0]
    assert step.retry_count == 1 and step.status == "succeeded"


@pytest.mark.asyncio
async def test_invalid_final_output_fails_run_and_retains_inference_audit(loop_runtime):
    session, identifier, model, _ = loop_runtime
    model.side_effect = [completion("Not JSON")]
    result = await execute(identifier)
    assert result.status == "failed"
    assert (await fetch(session, "SELECT status FROM agent_step", {}))[0].status == "failed"
    assert (await fetch(session, "SELECT status FROM ai_run", {}))[0].status == "succeeded"


@pytest.mark.asyncio
@pytest.mark.parametrize("with_tools", [False, True])
async def test_pause_during_model_request_preserves_paid_response_for_resume(
    loop_runtime, with_tools
):
    session, identifier, model, client = loop_runtime

    async def paused_response(**kwargs):
        await fetch(
            session,
            "UPDATE agent_run SET status='paused',updated_at=clock_timestamp() RETURNING id",
            {},
        )
        await session.commit()
        if with_tools:
            return completion(
                calls=[AgentToolCall("saved-call", "mal.search_anime", {"query": "Anime"})]
            )
        return completion('{"decision":"not_found"}')

    model.side_effect = paused_response
    paused = await execute(identifier)
    assert paused.status == "paused"
    audit = (await fetch(session, "SELECT status FROM ai_run", {}))[0]
    assert audit.status == "succeeded"
    assert (await fetch(session, "SELECT budget FROM agent_run", {}))[0].budget["steps_used"] == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_message", {}))[0].n == 2
    model.side_effect = [completion('{"decision":"not_found"}')]
    result = await execute(identifier, resume=True)
    assert result.status == "succeeded", result.error
    assert model.await_count == (2 if with_tools else 1)
    assert client.search_anime.call_count == (1 if with_tools else 0)
    run = (await fetch(session, "SELECT budget,checkpoint FROM agent_run", {}))[0]
    assert run.budget["steps_used"] == (3 if with_tools else 1)
    assert run.budget["input_tokens_used"] == (24 if with_tools else 12)
    assert run.checkpoint["message_count"] == (5 if with_tools else 3)


@pytest.mark.asyncio
async def test_resume_finishes_saved_final_response_without_another_model_request(loop_runtime):
    session, identifier, model, _ = loop_runtime
    model.side_effect = [completion('{"decision":"not_found"}')]
    execution = await agent_loop.claim(identifier, resume=False)
    await agent_loop.initialize(execution, "System", "Find anime")
    await agent_loop.model_turn(execution, use_case="mal_recall", tools=[])
    await fetch(
        session,
        "UPDATE agent_run SET status='paused',updated_at=clock_timestamp() RETURNING id",
        {},
    )
    await session.commit()
    result = await execute(identifier, resume=True)
    assert result.status == "succeeded", result.error
    assert result.output["decision"] == "not_found"
    assert model.await_count == 1
    assert (await fetch(session, "SELECT budget FROM agent_run", {}))[0].budget["steps_used"] == 1
    assert (await fetch(session, "SELECT error FROM ai_run", {}))[0].error == ""


@pytest.mark.asyncio
async def test_resume_completes_model_step_after_all_tool_replies_committed(
    loop_runtime, monkeypatch
):
    session, identifier, model, client = loop_runtime
    with monkeypatch.context() as patch:
        patch.setattr(
            agent_loop,
            "finish_tool_turn",
            AsyncMock(side_effect=agent_loop.ExecutionStopped("Interrupted")),
        )
        interrupted = await execute(identifier)
    assert interrupted.status == "running"
    await fetch(
        session,
        "UPDATE agent_run SET status='paused',updated_at=clock_timestamp() RETURNING id",
        {},
    )
    await session.commit()
    result = await execute(identifier, resume=True)
    assert result.status == "succeeded", result.error
    assert model.await_count == 2
    client.search_anime.assert_called_once()
    rows = await fetch(session, "SELECT status FROM agent_step", {})
    assert all(row.status == "succeeded" for row in rows)
    assert (await fetch(session, "SELECT budget FROM agent_run", {}))[0].budget["steps_used"] == 3


@pytest.mark.asyncio
async def test_legacy_completed_final_step_resumes_without_recharging_model_usage(loop_runtime):
    session, identifier, model, _ = loop_runtime
    model.side_effect = [completion('{"decision":"not_found"}')]
    execution = await agent_loop.claim(identifier, resume=False)
    await agent_loop.initialize(execution, "System", "Find anime")
    step, inference_id, response = await agent_loop.model_turn(
        execution, use_case="mal_recall", tools=[]
    )
    output = agent_loop.final_output(response.content, FinalOutput)
    await agent_runs.finish_step(session, step, output)
    await inference.store_result(session, inference_id, output, response.usage)
    await fetch(
        session,
        "UPDATE ai_run SET input_metadata="
        "jsonb_build_object('step_id',CAST(:step AS text)) RETURNING id",
        {"step": str(step)},
    )
    await fetch(
        session,
        "UPDATE agent_run SET status='paused',updated_at=clock_timestamp() RETURNING id",
        {},
    )
    await session.commit()
    result = await execute(identifier, resume=True)
    assert result.status == "succeeded", result.error
    assert result.output["decision"] == "not_found"
    assert model.await_count == 1
    budget = (await fetch(session, "SELECT budget FROM agent_run", {}))[0].budget
    assert budget["steps_used"] == 1 and budget["input_tokens_used"] == 12


@pytest.mark.asyncio
async def test_recovery_closes_legacy_queued_steps_and_their_inference_audit(loop_runtime):
    session, identifier, _, _ = loop_runtime
    step = await agent_runs.create_step(
        session, run_id=identifier, skill="", payload={}, kind="model"
    )
    await fetch(
        session, "UPDATE agent_step SET status='queued' WHERE id=:id RETURNING id", {"id": step}
    )
    await session.commit()
    audit = await inference.start_run(
        payload={}, use_case="mal_recall", prompt_version="legacy", metadata={}, agent_step_id=step
    )
    result = await execute(identifier)
    assert result.status == "succeeded", result.error
    assert (await fetch(session, "SELECT status FROM agent_step WHERE id=:id", {"id": step}))[
        0
    ].status == "failed"
    assert (await fetch(session, "SELECT status FROM ai_run WHERE id=:id", {"id": audit}))[
        0
    ].status == "failed"
