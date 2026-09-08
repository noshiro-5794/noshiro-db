"""Open-ended agent loop driver with native tool calling.

The loop is the DeepSeek-Harness-style counterpart of the deterministic
workflow executor: the model sees the full durable transcript, may emit any
number of tool calls, results are appended back, and the loop continues until
the model returns a final answer without tool calls.

Each model turn is persisted as an ``AgentStep`` with per-call
``ToolInvocation`` audit rows and an ``AIRun`` inference record; the transcript
itself lives in ``AgentMessage`` so a paused or interrupted run can replay
exactly what the model has already seen.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db.models import Max
from django.utils import timezone
from pydantic import BaseModel

from apps.ai.models import (
    AgentMessage,
    AgentRun,
    AgentStep,
    AIRun,
)
from apps.ai.runtime.budget import BudgetManager
from apps.ai.runtime.checkpoint import CheckpointManager
from apps.ai.runtime.executor import StepExecutor
from apps.ai.runtime.state_machine import (
    AgentRunStateMachine,
    AgentStepStateMachine,
    RunTransition,
    StepTransition,
)
from apps.ai.runtime.transcript import append_message, messages_for_provider
from apps.ai.skills.registry import create_default_skill_registry
from apps.ai.tools.registry import create_default_tool_registry
from integrations.ai.gateway import AgentCompletion, ai_gateway


@dataclass
class AgentLoopDriver:
    """Run one open-ended agent task to a terminal state."""

    executor: StepExecutor | None = None
    gateway: Any = ai_gateway
    max_attempts_per_turn: int = 3

    def __post_init__(self) -> None:
        self._skill_registry = create_default_skill_registry()
        if self.executor is None:
            self._tool_registry = create_default_tool_registry()
            self.executor = StepExecutor(
                tool_registry=self._tool_registry,
                skill_registry=self._skill_registry,
            )
        else:
            self._tool_registry = getattr(self.executor, "_tool_registry", None)

    def run(
        self,
        run: AgentRun,
        *,
        system_prompt: str,
        user_prompt: str,
        tool_names: list[str] | None = None,
        skill_name: str = "",
        output_model: type[BaseModel] | None = None,
        use_case: str = "agent_loop",
    ) -> AgentRun:
        run = self._start_or_resume(run)
        if run.status not in {
            AgentRun.Status.RUNNING,
            AgentRun.Status.QUEUED,
        }:
            return AgentRun.objects.get(pk=run.pk)

        if not AgentMessage.objects.filter(run=run).exists():
            append_message(
                run=run,
                role=AgentMessage.Role.SYSTEM,
                content=system_prompt,
            )
            append_message(
                run=run,
                role=AgentMessage.Role.USER,
                content=user_prompt,
            )

        tool_names = self._normalize_tool_names(tool_names)
        budget = BudgetManager.load(run)
        try:
            while True:
                run = AgentRun.objects.get(pk=run.pk)
                if budget.is_exhausted:
                    self._fail(run, f"Budget exhausted: {budget.exhaustion_reason}")
                    return AgentRun.objects.get(pk=run.pk)

                step, air_run = self._start_model_turn(
                    run=run,
                    skill_name=skill_name,
                    use_case=use_case,
                )
                completion = self._complete_turn(
                    run=run,
                    step=step,
                    air_run=air_run,
                    tool_names=tool_names,
                    use_case=use_case,
                )
                budget.record_execution(
                    input_tokens=_int_or_zero(completion.usage.get("input_tokens")),
                    output_tokens=_int_or_zero(completion.usage.get("output_tokens")),
                    cost=Decimal("0"),
                )
                BudgetManager.save(run, budget)

                if not completion.tool_calls:
                    return self._finish_turn(
                        run=run,
                        step=step,
                        air_run=air_run,
                        completion=completion,
                        skill_name=skill_name,
                        output_model=output_model,
                    )

                self._execute_tool_calls(
                    run=run,
                    parent_step=step,
                    air_run=air_run,
                    completion=completion,
                    tool_names=tool_names,
                )
                self._succeed_step(
                    step=step,
                    output={
                        "kind": "tool_turn",
                        "tool_calls": len(completion.tool_calls),
                    },
                )
        except Exception as exc:
            self._fail(run, f"{type(exc).__name__}: {exc}"[:4000])
            return AgentRun.objects.get(pk=run.pk)

    def _start_or_resume(self, run: AgentRun) -> AgentRun:
        run = AgentRun.objects.get(pk=run.pk)
        if run.status == AgentRun.Status.QUEUED:
            AgentRunStateMachine(run).transition(RunTransition.START)
        elif run.status == AgentRun.Status.PAUSED:
            AgentRunStateMachine(run).transition(RunTransition.RESUME)
        self._recover_inflight(run)
        return AgentRun.objects.get(pk=run.pk)

    @staticmethod
    def _recover_inflight(run: AgentRun) -> None:
        """Make an interrupted agent run safely resumable."""
        AgentStep.objects.filter(run=run, status=AgentStep.Status.RUNNING).update(
            status=AgentStep.Status.FAILED,
            error="Agent run was interrupted before the turn completed.",
            finished_at=timezone.now(),
        )
        rows = list(
            AgentMessage.objects.filter(run=run)
            .order_by("sequence")
            .values_list(
                "sequence",
                "role",
                "tool_calls",
            )
        )
        for index, (sequence, role, tool_calls) in enumerate(rows):
            if role != AgentMessage.Role.ASSISTANT or not tool_calls:
                continue
            next_role = rows[index + 1][1] if index + 1 < len(rows) else None
            if next_role != AgentMessage.Role.TOOL:
                AgentMessage.objects.filter(run=run, sequence__gte=sequence).delete()
                return

    def _normalize_tool_names(
        self,
        tool_names: list[str] | None,
    ) -> set[str]:
        if tool_names is None:
            if self._tool_registry is None:
                raise ValueError(
                    "tool_names are required when a custom executor is provided."
                )
            return {tool.name for tool in self._tool_registry.list_all()}
        if self._tool_registry is None:
            raise ValueError("No tool registry is available for this driver.")
        unknown = [name for name in tool_names if name not in self._tool_registry]
        if unknown:
            raise ValueError(f"Unknown tools requested: {', '.join(unknown)}")
        return set(tool_names)

    def _start_model_turn(
        self,
        *,
        run: AgentRun,
        skill_name: str,
        use_case: str,
    ) -> tuple[AgentStep, AIRun]:
        sequence = self._next_sequence(run)
        step = AgentStep.objects.create(
            run=run,
            sequence=sequence,
            kind=AgentStep.Kind.MODEL,
            status=AgentStep.Status.QUEUED,
            skill_name=skill_name,
            skill_version=self._skill_version(skill_name),
            input={
                "use_case": use_case,
                "system_prompt_marker": "stored_in_transcript",
            },
        )
        AgentStepStateMachine(step).transition(StepTransition.START)
        air_run = AIRun.objects.create(
            agent_step=step,
            use_case=use_case,
            provider=self.gateway.provider_name,
            model=self.gateway.resolve_model(use_case),
            prompt_version=use_case,
            input_hash=_payload_hash({"turn": step.sequence}),
            input_metadata={"step_id": str(step.pk)},
            status=AIRun.Status.RUNNING,
            started_at=timezone.now(),
        )
        return step, air_run

    def _complete_turn(
        self,
        *,
        run: AgentRun,
        step: AgentStep,
        air_run: AIRun,
        tool_names: set[str],
        use_case: str,
    ) -> AgentCompletion:
        transcript = messages_for_provider(run)
        tools = [
            definition.to_openai_schema()
            for definition in self._tool_registry.list_all()
            if definition.name in tool_names
        ]
        last_error: Exception | None = None
        for attempt in range(self.max_attempts_per_turn):
            started = timezone.now()
            try:
                completion = self.gateway.complete_agent(
                    messages=transcript,
                    tools=tools or None,
                    use_case=use_case,
                )
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= self.max_attempts_per_turn:
                    self._mark_airun_failed(
                        air_run=air_run,
                        error=exc,
                        started=started,
                    )
                    raise
                time.sleep(min(2**attempt, 5))
                continue
            append_message(
                run=run,
                role=AgentMessage.Role.ASSISTANT,
                content=completion.content,
                tool_calls=[
                    {
                        "id": call.id,
                        "name": call.name,
                        "arguments": call.arguments,
                    }
                    for call in completion.tool_calls
                ],
            )
            air_run.status = AIRun.Status.SUCCEEDED
            air_run.model = completion.model
            air_run.output = {
                "content": completion.content[:1_000_000],
                "tool_calls": [
                    {
                        "id": call.id,
                        "name": call.name,
                        "arguments": call.arguments,
                    }
                    for call in completion.tool_calls
                ],
            }
            air_run.input_tokens = _int_or_zero(completion.usage.get("input_tokens"))
            air_run.output_tokens = _int_or_zero(completion.usage.get("output_tokens"))
            air_run.finished_at = timezone.now()
            air_run.save(
                update_fields=[
                    "status",
                    "model",
                    "output",
                    "input_tokens",
                    "output_tokens",
                    "finished_at",
                ]
            )
            return completion
        if last_error is not None:
            raise last_error
        raise RuntimeError("Agent model turn exhausted its retry budget.")

    def _execute_tool_calls(
        self,
        *,
        run: AgentRun,
        parent_step: AgentStep,
        air_run: AIRun,
        completion: AgentCompletion,
        tool_names: set[str],
    ) -> None:
        for _index, call in enumerate(completion.tool_calls):
            if call.name not in tool_names:
                append_message(
                    run=run,
                    role=AgentMessage.Role.TOOL,
                    content=json.dumps(
                        {"error": f"Tool '{call.name}' is not allowed for this run."},
                        ensure_ascii=False,
                    ),
                    name=call.name,
                    tool_call_id=call.id,
                )
                continue
            child = AgentStep.objects.create(
                run=run,
                parent=parent_step,
                sequence=self._next_sequence(run),
                kind=AgentStep.Kind.TOOL,
                status=AgentStep.Status.QUEUED,
                input={
                    "tool_name": call.name,
                    "parameters": call.arguments,
                },
            )
            result = self.executor.execute(run, child, BudgetManager.load(run))
            content = (
                json.dumps(result.output, ensure_ascii=False, default=str)
                if result.output is not None
                else json.dumps(
                    {"error": result.error or "Tool failed without output"},
                    ensure_ascii=False,
                )
            )
            append_message(
                run=run,
                role=AgentMessage.Role.TOOL,
                content=content,
                name=call.name,
                tool_call_id=call.id,
            )
            if result.error:
                AgentRun.objects.filter(pk=run.pk).update(
                    error=result.error[:4000],
                    updated_at=timezone.now(),
                )
        tool_outputs = list(
            AgentMessage.objects.filter(run=run, role=AgentMessage.Role.TOOL)
            .order_by("-sequence")
            .values_list("content", flat=True)[: len(completion.tool_calls)]
        )
        air_run.output = {
            **(air_run.output or {}),
            "tool_outputs": list(reversed(tool_outputs)),
        }
        air_run.save(update_fields=["output"])

    def _finish_turn(
        self,
        *,
        run: AgentRun,
        step: AgentStep,
        air_run: AIRun,
        completion: AgentCompletion,
        skill_name: str,
        output_model: type[BaseModel] | None,
    ) -> AgentRun:
        if not completion.content.strip():
            raise ValueError("Model returned an empty final answer.")
        final_output: dict[str, Any]
        schema = output_model
        if schema is None and skill_name:
            schema = self._skill_registry.get(skill_name).output_model
        if schema is not None:
            try:
                parsed = _extract_json_object(completion.content)
                if not isinstance(parsed, dict):
                    raise ValueError("Skill output must be a JSON object.")
                final_output = schema.model_validate(parsed).model_dump(mode="json")
            except Exception as exc:
                raise ValueError(f"Invalid final skill output: {exc}") from exc
        else:
            final_output = {"content": completion.content}
        air_run.output = final_output
        air_run.save(update_fields=["output"])
        self._succeed_step(step=step, output=final_output)
        run = AgentRun.objects.get(pk=run.pk)
        AgentRunStateMachine(run).transition(RunTransition.SUCCEED)
        CheckpointManager.save(run)
        return AgentRun.objects.get(pk=run.pk)

    def _succeed_step(self, *, step: AgentStep, output: dict[str, Any]) -> None:
        step = AgentStep.objects.get(pk=step.pk)
        if AgentStepStateMachine(step).transition(StepTransition.SUCCEED):
            AgentStep.objects.filter(pk=step.pk).update(
                output=output,
                finished_at=timezone.now(),
            )

    def _mark_airun_failed(
        self,
        *,
        air_run: AIRun,
        error: Exception,
        started,
    ) -> None:
        air_run.status = AIRun.Status.FAILED
        air_run.error = f"{type(error).__name__}: {error}"[:4000]
        air_run.finished_at = timezone.now()
        air_run.save(update_fields=["status", "error", "finished_at"])

    @staticmethod
    def _fail(run: AgentRun, error: str) -> None:
        run = AgentRun.objects.get(pk=run.pk)
        if AgentRunStateMachine(run).transition(RunTransition.FAIL):
            AgentRun.objects.filter(pk=run.pk).update(error=error[:4000])
            CheckpointManager.save(run)

    @staticmethod
    def _next_sequence(run: AgentRun) -> int:
        current = AgentStep.objects.filter(run=run).aggregate(value=Max("sequence"))[
            "value"
        ]
        return int(current or 0) + 1

    @staticmethod
    def _skill_version(skill_name: str) -> str:
        if not skill_name:
            return ""
        return create_default_skill_registry().get(skill_name).version


def _int_or_zero(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _payload_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _extract_json_object(content: str) -> dict[str, Any]:
    """Extract the first balanced JSON object from a model response."""
    cleaned = re.sub(r"```(?:json)?", "", content, flags=re.IGNORECASE).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Model response does not contain a JSON object.")
    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON output must be an object.")
    return parsed
