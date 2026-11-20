"""Durable native tool calling with resumable transcripts and owned run updates."""

import asyncio
import json
import os
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.knowledge import agent_runs, checkpoints, retrieval, transcript
from api.contexts.knowledge.budget import Budget
from api.db import fetch
from api.shared import inference
from api.shared.ai import AgentCompletion, AgentToolCall, AIError, complete_agent, model_for
from api.worker import provider_search
from api.worker.session import session_scope


class ExecutionStopped(RuntimeError):
    """A run is controlled or owned by another invocation."""


class BudgetExhausted(RuntimeError):
    """A configured execution limit has been reached."""


@dataclass(slots=True)
class Execution:
    run_id: UUID
    version: datetime


@dataclass(frozen=True, slots=True)
class RunResult:
    id: UUID
    status: str
    output: dict[str, Any]
    error: str


async def own(session: AsyncSession, execution: Execution) -> Any:
    rows = await fetch(
        session,
        "SELECT * FROM agent_run WHERE id=:id AND status='running' "
        "AND updated_at=:version FOR UPDATE",
        {"id": execution.run_id, "version": execution.version},
    )
    if not rows:
        raise ExecutionStopped("Agent execution is no longer owned by this invocation.")
    return rows[0]


async def claim(run_id: UUID, *, resume: bool) -> Execution | None:
    async with session_scope() as session:
        rows = await fetch(
            session,
            "SELECT *,updated_at<clock_timestamp()-make_interval(secs=>:seconds) AS is_stale "
            "FROM agent_run WHERE id=:id FOR UPDATE",
            {
                "id": run_id,
                "seconds": max(60, int(os.environ.get("AI_AGENT_STALE_SECONDS", "3900"))),
            },
        )
        if not rows:
            raise LookupError("Agent run not found.")
        row = rows[0]
        eligible = (
            row.status == "queued"
            or (row.status == "paused" and resume)
            or (row.status == "running" and row.is_stale)
        )
        if not eligible:
            return None
        await agent_runs.recover_interrupted(
            session, run_id, "Agent run was interrupted before the turn completed."
        )
        version = (
            await fetch(
                session,
                "UPDATE agent_run SET status='running',started_at=COALESCE(started_at,now()),"
                "finished_at=NULL,updated_at=clock_timestamp() WHERE id=:id RETURNING updated_at",
                {"id": run_id},
            )
        )[0].updated_at
    return Execution(run_id, version)


async def update_budget(session: AsyncSession, execution: Execution, budget: Budget) -> datetime:
    await own(session, execution)
    rows = await fetch(
        session,
        "UPDATE agent_run SET budget=CAST(:budget AS jsonb),updated_at=clock_timestamp() "
        "WHERE id=:id RETURNING updated_at",
        {"id": execution.run_id, "budget": budget.model_dump_json()},
    )
    version: datetime = rows[0].updated_at
    return version


async def read_result(run_id: UUID) -> RunResult:
    async with session_scope() as session:
        rows = await fetch(
            session, "SELECT status,error FROM agent_run WHERE id=:id", {"id": run_id}
        )
        if not rows:
            raise LookupError("Agent run not found.")
        outputs = await fetch(
            session,
            "SELECT output FROM agent_step WHERE run_id=:id ORDER BY sequence DESC LIMIT 1",
            {"id": run_id},
        )
        return RunResult(
            run_id, rows[0].status, (outputs[0].output or {}) if outputs else {}, rows[0].error
        )


async def initialize(execution: Execution, system_prompt: str, user_prompt: str) -> Budget:
    async with session_scope() as session:
        row = await own(session, execution)
        budget = Budget.model_validate(row.budget or {})
        messages = await fetch(
            session,
            "SELECT 1 FROM agent_message WHERE run_id=:id LIMIT 1",
            {"id": execution.run_id},
        )
        if not messages:
            await transcript.append(
                session, run_id=execution.run_id, role="system", content=system_prompt
            )
            await transcript.append(
                session, run_id=execution.run_id, role="user", content=user_prompt
            )
        return budget


async def finish(execution: Execution, *, status: str, error: str = "") -> None:
    async with session_scope() as session:
        await store_final(session, execution, status=status, error=error)


async def store_final(
    session: AsyncSession, execution: Execution, *, status: str, error: str = ""
) -> None:
    await own(session, execution)
    if status == "failed":
        await agent_runs.recover_interrupted(session, execution.run_id, error[:4000])
    await fetch(
        session,
        "UPDATE agent_run SET status=:status,error=:error,finished_at=now() "
        "WHERE id=:id RETURNING id",
        {"id": execution.run_id, "status": status, "error": error[:4000]},
    )
    snapshot = await checkpoints.capture(session, execution.run_id)
    await fetch(
        session,
        "UPDATE agent_run SET checkpoint=CAST(:checkpoint AS jsonb),"
        "updated_at=clock_timestamp() "
        "WHERE id=:id RETURNING id",
        {"id": execution.run_id, "checkpoint": json.dumps(snapshot)},
    )


def final_output(content: str, output_model: type[BaseModel] | None) -> dict[str, Any]:
    if not content.strip():
        raise ValueError("Model returned an empty final answer.")
    if output_model is None:
        return {"content": content}
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Skill output must be a JSON object.")
        return output_model.model_validate(parsed).model_dump(mode="json")
    except (ValueError, TypeError) as error:
        raise ValueError(f"Invalid final skill output: {error}") from error


async def current_budget(execution: Execution) -> Budget:
    async with session_scope() as session:
        row = await own(session, execution)
        return Budget.model_validate(row.budget or {})


async def save_completion(
    session: AsyncSession,
    execution: Execution,
    inference_id: UUID,
    completion: AgentCompletion,
    *,
    append_message: bool,
) -> Budget:
    row = (
        await fetch(
            session,
            "SELECT budget FROM agent_run WHERE id=:id FOR UPDATE",
            {"id": execution.run_id},
        )
    )[0]
    recorded = (
        await fetch(session, "SELECT input_metadata FROM ai_run WHERE id=:id", {"id": inference_id})
    )[0].input_metadata or {}
    budget = Budget.model_validate(row.budget or {})
    calls = [
        {"id": call.id, "name": call.name, "arguments": call.arguments}
        for call in completion.tool_calls
    ]
    await inference.store_result(
        session,
        inference_id,
        {"content": completion.content[:1_000_000], "tool_calls": calls},
        completion.usage,
        model=completion.model,
    )
    if not recorded.get("budget_recorded"):
        budget.record_execution(completion.usage)
        await fetch(
            session,
            "UPDATE agent_run SET budget=CAST(:budget AS jsonb) WHERE id=:id RETURNING id",
            {"id": execution.run_id, "budget": budget.model_dump_json()},
        )
        await fetch(
            session,
            "UPDATE ai_run SET input_metadata=input_metadata||CAST(:flag AS jsonb) "
            "WHERE id=:id RETURNING id",
            {"id": inference_id, "flag": json.dumps({"budget_recorded": True})},
        )
    if append_message:
        await transcript.append(
            session,
            run_id=execution.run_id,
            role="assistant",
            content=completion.content,
            tool_calls=calls,
        )
    return budget


async def model_turn(
    execution: Execution, *, use_case: str, tools: list[dict[str, Any]]
) -> tuple[UUID, UUID, AgentCompletion]:
    async with session_scope() as session:
        await own(session, execution)
        step = await agent_runs.create_step(
            session,
            run_id=execution.run_id,
            skill="",
            kind="model",
            payload={"use_case": use_case, "system_prompt_marker": "stored_in_transcript"},
            first_sequence=1,
        )
        messages = await transcript.messages(session, execution.run_id)
    inference_id = await inference.start_run(
        payload={"messages": messages},
        use_case=use_case,
        prompt_version=use_case,
        metadata={"step_id": str(step), "transcript_message_count": len(messages)},
        agent_step_id=step,
        model=model_for(use_case),
    )
    maximum = max(1, int(os.environ.get("AI_AGENT_MAX_ATTEMPTS", "3")))
    for attempt in range(maximum):
        budget = await current_budget(execution)
        if budget.exhaustion_reason:
            raise BudgetExhausted(f"Budget exhausted: {budget.exhaustion_reason}")
        try:
            completion = await complete_agent(
                messages=messages, tools=tools or None, use_case=use_case
            )
        except Exception as error:
            async with session_scope() as session:
                row = (
                    await fetch(
                        session,
                        "SELECT * FROM agent_run WHERE id=:id FOR UPDATE",
                        {"id": execution.run_id},
                    )
                )[0]
                budget = Budget.model_validate(row.budget or {})
                budget.record_execution()
                await fetch(
                    session,
                    "UPDATE agent_run SET budget=CAST(:budget AS jsonb) WHERE id=:id RETURNING id",
                    {"id": execution.run_id, "budget": budget.model_dump_json()},
                )
                await fetch(
                    session,
                    "UPDATE agent_step SET retry_count=:attempt,error=:error "
                    "WHERE id=:id RETURNING id",
                    {
                        "id": step,
                        "attempt": attempt + 1,
                        "error": f"{type(error).__name__}: {error}"[:4000],
                    },
                )
                owned = row.status == "running" and row.updated_at == execution.version
                version = await update_budget(session, execution, budget) if owned else None
            if version is None:
                await inference.fail_run(inference_id, error)
                raise ExecutionStopped("Agent execution changed during model retrieval.") from error
            execution.version = version
            if not isinstance(error, AIError) or not error.retryable or attempt + 1 >= maximum:
                await inference.fail_run(inference_id, error)
                raise
            await asyncio.sleep(min(2**attempt, 5))
            continue
        try:
            async with session_scope() as session:
                await own(session, execution)
                budget = await save_completion(
                    session, execution, inference_id, completion, append_message=True
                )
                version = await update_budget(session, execution, budget)
        except ExecutionStopped:
            async with session_scope() as session:
                await save_completion(
                    session, execution, inference_id, completion, append_message=False
                )
            raise
        execution.version = version
        return step, inference_id, completion
    raise RuntimeError("Agent model turn exhausted its retry budget.")


async def tool_result(
    execution: Execution, call: AgentToolCall, parent: UUID, allowed: set[str]
) -> dict[str, Any]:
    if call.name not in allowed:
        return {"error": f"Tool '{call.name}' is not allowed for this run."}
    async with session_scope() as session:
        await own(session, execution)
        completed = await fetch(
            session,
            "SELECT output,error,status FROM agent_step WHERE run_id=:id AND kind='tool' "
            "AND parent_id=:parent AND input->>'tool_call_id'=:call "
            "AND status IN ('succeeded','failed') "
            "ORDER BY sequence DESC LIMIT 1",
            {"id": execution.run_id, "call": call.id, "parent": parent},
        )
        if completed:
            return (
                (completed[0].output or {})
                if completed[0].status == "succeeded"
                else {"error": completed[0].error or "Tool failed without output"}
            )
    definition = retrieval.TOOLS[call.name]

    async def guard(session: AsyncSession) -> None:
        await own(session, execution)

    try:
        output = await provider_search.invoke(
            run_id=execution.run_id,
            tool=call.name,
            permission=definition.permission,
            parameters=call.arguments,
            handler=lambda: definition.execute(call.arguments),
            before_write=guard,
            parent_step_id=parent,
            tool_call_id=call.id,
            artifact_mode="snapshot",
        )
        payload: dict[str, Any] = output.model_dump(mode="json")
        return payload
    except ExecutionStopped:
        raise
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}"[:4000]}


async def execute_tools(
    execution: Execution,
    parent: UUID,
    calls: list[AgentToolCall],
    allowed: set[str],
) -> None:
    for call in calls:
        budget = await current_budget(execution)
        if budget.exhaustion_reason:
            raise BudgetExhausted(f"Budget exhausted: {budget.exhaustion_reason}")
        output = await tool_result(execution, call, parent, allowed)
        async with session_scope() as session:
            row = await own(session, execution)
            budget = Budget.model_validate(row.budget or {})
            budget.record_execution()
            await transcript.append(
                session,
                run_id=execution.run_id,
                role="tool",
                name=call.name,
                tool_call_id=call.id,
                content=json.dumps(output, ensure_ascii=False, default=str),
            )
            version = await update_budget(session, execution, budget)
        execution.version = version
    await finish_tool_turn(execution, parent, calls)


async def finish_tool_turn(execution: Execution, parent: UUID, calls: list[AgentToolCall]) -> None:
    async with session_scope() as session:
        await own(session, execution)
        audits = await fetch(
            session,
            "SELECT id,output FROM ai_run WHERE agent_step_id=:id ORDER BY created_at DESC LIMIT 1",
            {"id": parent},
        )
        call_count = len(calls)
        if audits:
            audit_output = audits[0].output or {}
            original_calls = audit_output.get("tool_calls") or []
            call_count = len(original_calls)
            assistants = await fetch(
                session,
                "SELECT sequence FROM agent_message WHERE run_id=:id AND role='assistant' "
                "AND tool_calls @> CAST(:call AS jsonb) ORDER BY sequence DESC LIMIT 1",
                {"id": execution.run_id, "call": json.dumps([{"id": calls[0].id}])},
            )
            outputs = await fetch(
                session,
                "SELECT content FROM agent_message WHERE run_id=:id AND role='tool' "
                "AND sequence>:sequence AND tool_call_id=ANY(:calls) ORDER BY sequence",
                {
                    "id": execution.run_id,
                    "sequence": assistants[0].sequence if assistants else 0,
                    "calls": [call["id"] for call in original_calls],
                },
            )
            await fetch(
                session,
                "UPDATE ai_run SET output=CAST(:output AS jsonb) WHERE id=:id RETURNING id",
                {
                    "id": audits[0].id,
                    "output": json.dumps(
                        {**audit_output, "tool_outputs": [row.content for row in outputs]}
                    ),
                },
            )
        await agent_runs.finish_step(
            session, parent, {"kind": "tool_turn", "tool_calls": call_count}
        )


async def recover_pending(execution: Execution, allowed: set[str]) -> None:
    async with session_scope() as session:
        await own(session, execution)
        rows = await fetch(
            session,
            "SELECT * FROM agent_message WHERE run_id=:id ORDER BY sequence",
            {"id": execution.run_id},
        )
        latest = next((row for row in reversed(rows) if row.role == "assistant"), None)
        if latest is None or not latest.tool_calls:
            return
        replies = {
            row.tool_call_id
            for row in rows
            if row.role == "tool" and row.sequence > latest.sequence
        }
        pending = [
            AgentToolCall(call["id"], call["name"], call.get("arguments") or {})
            for call in latest.tool_calls
            if call["id"] not in replies
        ]
        parents = await fetch(
            session,
            "SELECT s.id FROM agent_step s JOIN ai_run a ON a.agent_step_id=s.id "
            "WHERE s.run_id=:id AND s.kind='model' "
            "AND a.output->'tool_calls' @> CAST(:call AS jsonb) "
            "ORDER BY s.sequence DESC LIMIT 1",
            {"id": execution.run_id, "call": json.dumps([{"id": latest.tool_calls[0]["id"]}])},
        )
        if not parents:
            raise ValueError("Pending tool calls have no durable model turn.")
        parent = UUID(str(parents[0].id))
        await fetch(
            session,
            "UPDATE agent_step SET status='running',error='',retry_count=retry_count+1 "
            "WHERE id=:id RETURNING id",
            {"id": parent},
        )
    if pending:
        await execute_tools(execution, parent, pending, allowed)
    else:
        await finish_tool_turn(
            execution,
            parent,
            [
                AgentToolCall(call["id"], call["name"], call.get("arguments") or {})
                for call in latest.tool_calls
            ],
        )


async def recover_completion(
    execution: Execution,
    output_model: type[BaseModel] | None,
) -> tuple[UUID, UUID, AgentCompletion] | None:
    """Reuse a saved response when execution stopped before its turn committed."""
    async with session_scope() as session:
        await own(session, execution)
        audits = await fetch(
            session,
            "SELECT a.*,s.id AS step_id,s.output AS step_output,s.status AS step_status "
            "FROM ai_run a "
            "JOIN agent_step s ON s.id=a.agent_step_id "
            "WHERE s.run_id=:id AND s.kind='model' "
            "ORDER BY s.sequence DESC,a.created_at DESC LIMIT 1",
            {"id": execution.run_id},
        )
        if not audits:
            return None
        audit = audits[0]
        output = audit.output or {}
        metadata = audit.input_metadata or {}
        count = metadata.get("transcript_message_count")
        if audit.status != "succeeded":
            return None
        messages = await transcript.messages(session, execution.run_id)
        if count is None:
            if (
                not messages
                or messages[-1]["role"] != "assistant"
                or messages[-1].get("tool_calls")
                or audit.step_status != "succeeded"
                or audit.step_output != output
            ):
                return None
            try:
                if final_output(messages[-1]["content"], output_model) != output:
                    return None
            except ValueError:
                return None
            # Legacy completed steps saved their budget before committing their output.
            await fetch(
                session,
                "UPDATE ai_run SET input_metadata=input_metadata||CAST(:metadata AS jsonb) "
                "WHERE id=:id RETURNING id",
                {"id": audit.id, "metadata": json.dumps({"budget_recorded": True})},
            )
            output = {"content": messages[-1]["content"], "tool_calls": []}
            count = len(messages) - 1
        if "tool_calls" not in output:
            return None
        completion = AgentCompletion(
            output.get("content") or "",
            audit.model,
            {
                "input_tokens": audit.input_tokens,
                "output_tokens": audit.output_tokens,
                "cost": str(audit.cost) if audit.cost is not None else None,
            },
            [
                AgentToolCall(call["id"], call["name"], call.get("arguments") or {})
                for call in output["tool_calls"]
            ],
        )
        missing = len(messages) == count
        appended_final = (
            not completion.tool_calls
            and len(messages) == count + 1
            and messages[-1]["role"] == "assistant"
            and messages[-1].get("content") == completion.content
        )
        if not missing and not appended_final:
            return None
        await fetch(
            session,
            "UPDATE agent_step SET status='running',error='',retry_count=retry_count+1 "
            "WHERE id=:id RETURNING id",
            {"id": audit.step_id},
        )
        budget = await save_completion(
            session, execution, audit.id, completion, append_message=missing
        )
        version = await update_budget(session, execution, budget)
        result = (UUID(str(audit.step_id)), UUID(str(audit.id)), completion)
    execution.version = version
    return result if not completion.tool_calls else None


async def finalize_response(
    execution: Execution,
    response: tuple[UUID, UUID, AgentCompletion],
    output_model: type[BaseModel] | None,
) -> None:
    step, inference_id, completion = response
    output = final_output(completion.content, output_model)
    async with session_scope() as session:
        await own(session, execution)
        await agent_runs.finish_step(session, step, output)
        await inference.store_result(
            session, inference_id, output, completion.usage, model=completion.model
        )
        await store_final(session, execution, status="succeeded")


async def run(
    run_id: UUID,
    *,
    system_prompt: str,
    user_prompt: str,
    tool_names: list[str] | None = None,
    output_model: type[BaseModel] | None = None,
    use_case: str = "agent_loop",
    resume: bool = False,
) -> RunResult:
    allowed = set(retrieval.TOOLS if tool_names is None else tool_names)
    unknown = allowed - set(retrieval.TOOLS)
    if unknown:
        raise ValueError(f"Unknown tools requested: {', '.join(sorted(unknown))}")
    execution = await claim(run_id, resume=resume)
    if execution is None:
        return await read_result(run_id)
    try:
        await initialize(execution, system_prompt, user_prompt)
        recovered = await recover_completion(execution, output_model)
        if recovered is not None:
            await finalize_response(execution, recovered, output_model)
            return await read_result(run_id)
        await recover_pending(execution, allowed)
        tools = [
            definition.schema() for name, definition in retrieval.TOOLS.items() if name in allowed
        ]
        while True:
            budget = await current_budget(execution)
            if budget.exhaustion_reason:
                raise BudgetExhausted(f"Budget exhausted: {budget.exhaustion_reason}")
            step, inference_id, completion = await model_turn(
                execution, use_case=use_case, tools=tools
            )
            if completion.tool_calls:
                await execute_tools(execution, step, completion.tool_calls, allowed)
                continue
            await finalize_response(execution, (step, inference_id, completion), output_model)
            break
    except ExecutionStopped:
        pass
    except Exception as error:
        with suppress(ExecutionStopped):
            await finish(
                execution, status="failed", error=f"{type(error).__name__}: {error}"[:4000]
            )
    return await read_result(run_id)
