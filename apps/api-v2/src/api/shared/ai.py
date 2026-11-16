"""A minimal async client for an OpenAI-compatible chat endpoint.

One call, JSON out, no retries: a failed generation is a failed draft, not a
batch to replay. The old service has the same provider configuration, so the two
see identical settings.
"""

from __future__ import annotations

import json
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


async def complete_json(
    *, system: str, payload: dict[str, Any], timeout: float = 60.0
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not settings.ai_base_url or not settings.ai_api_key:
        raise AIError("AI_AGENT_API_BASE_URL and AI_AGENT_API_KEY are required")
    if not await provider_available():
        raise AIError("AI provider is in account-failure cooldown")
    body = {
        "model": settings.ai_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
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
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise AIError("AI provider did not return a JSON object") from error
    if not isinstance(result, dict):
        raise AIError("AI provider did not return a JSON object")
    return result, data.get("usage", {})
