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


class AIError(RuntimeError):
    """The provider could not produce a usable answer."""


async def complete_json(
    *, system: str, payload: dict[str, Any], timeout: float = 60.0
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not settings.ai_base_url or not settings.ai_api_key:
        raise AIError("AI_AGENT_API_BASE_URL and AI_AGENT_API_KEY are required")
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
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(settings.ai_base_url, json=body, headers=headers)
    if response.status_code != 200:
        raise AIError(f"AI provider returned {response.status_code}: {response.text[:200]}")
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as error:
        raise AIError("AI provider did not return a JSON object") from error
    if not isinstance(result, dict):
        raise AIError("AI provider did not return a JSON object")
    return result, data.get("usage", {})
