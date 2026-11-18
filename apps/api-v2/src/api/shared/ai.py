"""Async OpenAI-compatible JSON and native tool-calling transport with usage accounting."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx

from api.config import settings
from api.shared.ai_availability import mark_unavailable, provider_available
from api.shared.outbound import proxy_for


class AIError(RuntimeError):
    """A classified failure from the model provider."""

    def __init__(
        self, message: str, *, status_code: int | None = None, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


async def request_completion(body: dict[str, Any], timeout: float) -> dict[str, Any]:
    if not settings.ai_base_url or not settings.ai_api_key:
        raise AIError("AI_AGENT_API_BASE_URL and AI_AGENT_API_KEY are required")
    if not await provider_available():
        raise AIError("AI provider is in account-failure cooldown")
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"}
    try:
        async with httpx.AsyncClient(
            timeout=timeout, proxy=proxy_for(settings.ai_base_url)
        ) as client:
            response = await client.post(settings.ai_base_url, json=body, headers=headers)
    except httpx.TransportError as error:
        raise AIError("AI provider transport failed", retryable=True) from error
    if response.status_code in {401, 402, 403}:
        await mark_unavailable(response.status_code)
    if response.status_code != 200:
        raise AIError(
            f"AI provider returned {response.status_code}",
            status_code=response.status_code,
            retryable=response.status_code == 429 or response.status_code >= 500,
        )
    try:
        data = response.json()
    except (ValueError, TypeError) as error:
        raise AIError("AI provider returned invalid JSON") from error
    if not isinstance(data, dict):
        raise AIError("AI provider returned an invalid completion response")
    return data


def model_for(use_case: str) -> str:
    if use_case in {"knowledge_qa", "user_agent", "user_agent_loop"}:
        return settings.ai_reasoning_model
    return settings.ai_model


def usage_with_cost(model: str, value: Any) -> dict[str, Any]:
    usage = dict(value) if isinstance(value, dict) else {}
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
    usage.update({"model": model, "input_tokens": input_tokens, "output_tokens": output_tokens})
    price = settings.ai_model_prices.get(model)
    if not isinstance(price, dict) or (input_tokens is None and output_tokens is None):
        return usage
    try:
        cost = (
            Decimal(str(price.get("input", 0))) * Decimal(int(input_tokens or 0))
            + Decimal(str(price.get("output", 0))) * Decimal(int(output_tokens or 0))
        ) / Decimal(1_000_000)
        if cost.is_finite() and cost >= 0:
            usage["cost"] = str(cost.quantize(Decimal("0.000001")))
    except (ArithmeticError, TypeError, ValueError):
        return usage
    return usage


async def complete_json(
    *, system: str, payload: dict[str, Any], timeout: float | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    data = await request_completion(
        {
            "model": settings.ai_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": settings.ai_max_output_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        },
        settings.ai_timeout_seconds if timeout is None else timeout,
    )
    try:
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise AIError("AI provider did not return a JSON object") from error
    if not isinstance(result, dict):
        raise AIError("AI provider did not return a JSON object")
    return result, usage_with_cost(str(data.get("model") or settings.ai_model), data.get("usage"))


@dataclass(frozen=True, slots=True)
class AgentToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentCompletion:
    content: str
    model: str
    usage: dict[str, Any]
    tool_calls: list[AgentToolCall] = field(default_factory=list)


def parse_tool_calls(value: Any) -> list[AgentToolCall]:
    if not isinstance(value, list):
        return []
    calls = []
    for item in value:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("id") or "")
        raw_function = item.get("function")
        function = raw_function if isinstance(raw_function, dict) else {}
        name = str(function.get("name") or "")
        raw_arguments = function.get("arguments") or "{}"
        try:
            arguments = (
                json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            )
        except (ValueError, TypeError):
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        if identifier and name:
            calls.append(AgentToolCall(identifier, name, arguments))
    return calls


async def complete_agent(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    use_case: str = "agent_loop",
    timeout: float | None = None,
) -> AgentCompletion:
    if not messages:
        raise AIError("Agent transcript must contain at least one message.")
    model = model_for(use_case)
    body: dict[str, Any] = {"model": model, "temperature": 0, "messages": messages}
    if tools:
        body["tools"] = tools
    data = await request_completion(
        body, settings.ai_timeout_seconds if timeout is None else timeout
    )
    try:
        message = data["choices"][0]["message"]
        if not isinstance(message, dict):
            raise TypeError("message")
        content = message.get("content") or ""
    except (KeyError, IndexError, TypeError) as error:
        raise AIError("AI provider returned an invalid agent response") from error
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    actual_model = str(data.get("model") or model)
    return AgentCompletion(
        content,
        actual_model,
        usage_with_cost(actual_model, data.get("usage")),
        parse_tool_calls(message.get("tool_calls")),
    )
