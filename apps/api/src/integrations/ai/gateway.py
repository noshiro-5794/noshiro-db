from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from integrations.ai.exceptions import AIProviderError
from shared.outbound import httpx_client_kwargs

logger = logging.getLogger(__name__)

# A provider that answers 402 does so for every request until someone tops the
# account up. Without a marker the matching dispatcher queues three hundred
# doomed calls every half hour and writes a failure row for each.
PROVIDER_BREAKER_KEY = "noshiro:ai:provider-unavailable"


class ModelTier(StrEnum):
    """Budget tiers. Batch work stays on Fast; user intent uses Reasoning."""

    FAST = "AI_FAST_MODEL"
    REASONING = "AI_REASONING_MODEL"


# Every offline/batch decision path is explicitly pinned to the cheap tier.
USE_CASE_TIERS: dict[str, ModelTier] = {
    "entity_matching": ModelTier.FAST,
    "entity_classification": ModelTier.FAST,
    "bangumi_link_search": ModelTier.FAST,
    "evidence_extraction": ModelTier.FAST,
    "conflict_detection": ModelTier.FAST,
    "info_completion": ModelTier.FAST,
    "field_normalization": ModelTier.FAST,
    "schedule_completion": ModelTier.FAST,
    "agent_loop": ModelTier.FAST,
    "mal_recall": ModelTier.FAST,
    # Interactive user-facing agent work needs stronger intent/database
    # reasoning than batch classification.
    "knowledge_qa": ModelTier.REASONING,
    "user_agent": ModelTier.REASONING,
    "user_agent_loop": ModelTier.REASONING,
}


class OpenAICompatibleGateway:
    provider_name = "openai_compatible"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    @property
    def breaker_ttl(self) -> int:
        return int(getattr(settings, "AI_PROVIDER_BREAKER_SECONDS", 900))

    @staticmethod
    def provider_available() -> bool:
        """False while the provider is known to be refusing every call."""
        return cache.get(PROVIDER_BREAKER_KEY) is None

    @classmethod
    def _open_breaker(cls, error: AIProviderError) -> None:
        ttl = int(getattr(settings, "AI_PROVIDER_BREAKER_SECONDS", 900))
        cache.set(PROVIDER_BREAKER_KEY, str(error)[:400], timeout=max(60, ttl))
        logger.warning(
            "AI provider marked unavailable for %ss: %s", ttl, str(error)[:200]
        )

    @staticmethod
    def _close_breaker() -> None:
        cache.delete(PROVIDER_BREAKER_KEY)

    def _post(self, *, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST with a bounded retry for failures that retrying can fix.

        Account failures (401/402/403) are terminal: they open the breaker and
        raise immediately instead of spending attempts on a call that cannot
        succeed.
        """
        attempts = max(1, int(getattr(settings, "AI_AGENT_MAX_ATTEMPTS", 3)))
        base_delay = float(getattr(settings, "AI_AGENT_RETRY_BASE_SECONDS", 2.0))
        last_error: AIProviderError | None = None
        for attempt in range(1, attempts + 1):
            if not self.provider_available():
                raise AIProviderError(
                    "AI provider is marked unavailable; skipping the call.",
                    retryable=True,
                )
            try:
                response = self.client.post(url, json=payload)
                response.raise_for_status()
                self._close_breaker()
                data = response.json()
            except httpx.HTTPStatusError as exc:
                error = AIProviderError(
                    f"AI provider returned {exc.response.status_code}: "
                    f"{exc.response.text[:300]}",
                    status_code=exc.response.status_code,
                )
            except (httpx.HTTPError, ValueError) as exc:
                error = AIProviderError(
                    f"AI provider request failed: {exc}", retryable=True
                )
            else:
                if isinstance(data, dict):
                    return data
                error = AIProviderError(
                    "AI provider returned a non-object payload.", retryable=False
                )
            last_error = error
            if error.is_account_problem:
                self._open_breaker(error)
                raise error
            if not error.retryable or attempt >= attempts:
                raise error
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logger.info(
                "Retrying AI provider call after %s (attempt %s/%s, %.1fs)",
                str(error)[:120],
                attempt,
                attempts,
                delay,
            )
            time.sleep(delay)
        raise last_error or AIProviderError("AI provider call failed.")

    def resolve_model(self, use_case: str) -> str:
        tier = USE_CASE_TIERS.get(use_case, ModelTier.REASONING)
        return getattr(settings, tier.value)

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if settings.AI_AGENT_API_KEY:
                headers["Authorization"] = f"Bearer {settings.AI_AGENT_API_KEY}"
            self._client = httpx.Client(
                **httpx_client_kwargs(
                    headers=headers,
                    timeout=settings.AI_AGENT_TIMEOUT,
                )
            )
        return self._client

    def complete_json(
        self,
        *,
        system_prompt: str,
        payload: dict[str, Any],
        use_case: str = "entity_matching",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not settings.AI_AGENT_API_KEY:
            raise AIProviderError("AI_AGENT_API_KEY is not configured.")
        model = self.resolve_model(use_case)
        result, usage = self._call(model, system_prompt, payload)
        return result, usage

    def complete_agent(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        use_case: str = "agent_loop",
    ) -> AgentCompletion:
        """Run one native tool-calling model turn over the given transcript."""
        if not settings.AI_AGENT_API_KEY:
            raise AIProviderError("AI_AGENT_API_KEY is not configured.")
        if not isinstance(messages, list) or not messages:
            raise AIProviderError("Agent transcript must contain at least one message.")
        request_payload: dict[str, Any] = {
            "model": self.resolve_model(use_case),
            "messages": messages,
            "temperature": 0,
        }
        if tools:
            request_payload["tools"] = tools
        data = self._post(url=settings.AI_AGENT_API_BASE_URL, payload=request_payload)
        try:
            message = data["choices"][0]["message"]
            model = str(data.get("model") or request_payload["model"])
            usage = data.get("usage") or {}
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError(
                f"AI provider returned an invalid agent response: {exc}",
                retryable=False,
            ) from exc
        content = message.get("content") if isinstance(message, dict) else ""
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False) if content else ""
        return AgentCompletion(
            content=content,
            tool_calls=_parse_tool_calls(message.get("tool_calls")),
            model=model,
            usage={
                "model": model,
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
            },
        )

    @staticmethod
    def _confidence(result: dict[str, Any]) -> Decimal:
        try:
            raw = result.get("confidence")
            if raw is None or isinstance(raw, bool):
                return Decimal("0")
            return Decimal(str(raw))
        except Exception:
            return Decimal("0")

    def _call(
        self,
        model: str,
        system_prompt: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        request_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        data = self._post(url=settings.AI_AGENT_API_BASE_URL, payload=request_payload)
        try:
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError(
                f"AI provider returned an invalid response: {exc}",
                retryable=False,
            ) from exc
        if not isinstance(result, dict):
            raise AIProviderError("AI provider JSON output must be an object.")
        usage = data.get("usage") or {}
        return result, {
            "model": model,
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
        }


ai_gateway = OpenAICompatibleGateway()


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


def _parse_tool_calls(raw: Any) -> list[AgentToolCall]:
    if not isinstance(raw, list):
        return []
    calls: list[AgentToolCall] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        call_id = str(item.get("id") or "")
        function = (
            item.get("function") if isinstance(item.get("function"), dict) else {}
        )
        name = str(function.get("name") or "")
        raw_arguments = function.get("arguments") or "{}"
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments)
            except (TypeError, ValueError):
                arguments = {}
        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments
        else:
            arguments = {}
        if not call_id or not name or not isinstance(arguments, dict):
            continue
        calls.append(AgentToolCall(id=call_id, name=name, arguments=arguments))
    return calls
