import pytest
from pydantic import Field

from apps.ai.models import (
    AgentMessage,
    AgentRun,
    AgentStep,
    AIRun,
    ToolInvocation,
)
from apps.ai.runtime.agent_loop import AgentLoopDriver, _extract_json_object
from apps.ai.runtime.executor import StepExecutor
from apps.ai.skills.registry import create_default_skill_registry
from apps.ai.tools.registry import (
    ToolDefinition,
    ToolInput,
    ToolOutput,
    ToolRegistry,
)
from integrations.ai.gateway import AgentCompletion, AgentToolCall

pytestmark = pytest.mark.django_db(transaction=True)


def test_extract_json_object_handles_explanation_and_code_fence() -> None:
    content = (
        "I found a match.\n```json\n"
        '{"decision": "found", "mal_id": 62954, '
        '"confidence": 0.97, "reason": "same title"}\n```'
    )

    parsed = _extract_json_object(content)

    assert parsed["mal_id"] == 62954


class EchoInput(ToolInput):
    value: str = Field(min_length=1)


class EchoOutput(ToolOutput):
    echoed: str


def _echo(value: EchoInput) -> EchoOutput:
    return EchoOutput(echoed=value.value)


class FakeToolGateway:
    provider_name = "fake_tool"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def resolve_model(self, use_case: str) -> str:
        return "fake/tool-model"

    def complete_agent(
        self,
        *,
        messages: list[dict],
        tools: list[dict] | None = None,
        use_case: str = "agent_loop",
    ) -> AgentCompletion:
        self.calls.append(str(tools))
        if len(self.calls) == 1:
            return AgentCompletion(
                content="",
                model="fake/tool-model",
                usage={"input_tokens": 10, "output_tokens": 5},
                tool_calls=[
                    AgentToolCall(
                        id="call_echo",
                        name="test.echo",
                        arguments={"value": "hello"},
                    )
                ],
            )
        return AgentCompletion(
            content='{"echoed": "hello"}',
            model="fake/tool-model",
            usage={"input_tokens": 10, "output_tokens": 5},
            tool_calls=[],
        )


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="test.echo",
            description="Echo a value.",
            input_model=EchoInput,
            output_model=EchoOutput,
            handler=_echo,
            permission="knowledge:read",
            records_evidence=False,
        )
    )
    return registry


def test_agent_loop_runs_tools_and_persists_transcript() -> None:
    registry = _registry()
    gateway = FakeToolGateway()
    driver = AgentLoopDriver(
        executor=StepExecutor(
            tool_registry=registry,
            skill_registry=create_default_skill_registry(),
        ),
        gateway=gateway,
    )
    run = AgentRun.objects.create(
        kind=AgentRun.Kind.EVALUATION,
        status=AgentRun.Status.QUEUED,
        title="loop echo",
        metadata={"scopes": ["knowledge:read"]},
        idempotency_scope="test",
        idempotency_key="echo-1",
    )

    finished = driver.run(
        run,
        system_prompt="Use the echo tool then answer.",
        user_prompt="echo hello",
        tool_names=["test.echo"],
        use_case="agent_loop",
    )

    finished.refresh_from_db()
    assert finished.status == AgentRun.Status.SUCCEEDED
    roles = list(
        AgentMessage.objects.filter(run=finished)
        .order_by("sequence")
        .values_list("role", flat=True)
    )
    assert roles == ["system", "user", "assistant", "tool", "assistant"]
    assert AgentStep.objects.filter(run=finished, kind=AgentStep.Kind.TOOL).count() == 1
    assert (
        AgentStep.objects.filter(run=finished, kind=AgentStep.Kind.MODEL).count() == 2
    )
    assert AIRun.objects.filter(agent_step__run=finished).count() == 2
    assert (
        AIRun.objects.filter(
            agent_step__run=finished, status=AIRun.Status.SUCCEEDED
        ).count()
        == 2
    )
    invocation = ToolInvocation.objects.get(step__run=finished)
    assert invocation.tool_name == "test.echo"
    assert invocation.status == ToolInvocation.Status.SUCCEEDED
    assert invocation.result == {"echoed": "hello"}
