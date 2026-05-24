from typing import Any

import httpx
from django.conf import settings


class AIClient:

    NAME_SYSTEM_PROMPT = """
You are an anime metadata normalization system.

Your task is to normalize any tag, role, format, or concept into ONE canonical Japanese word used in anime databases.

Rules:

1 Output ONLY ONE Japanese word.
2 No explanations.
3 No punctuation.
4 No extra text.
5 If the input is already Japanese, normalize it.
6 Understand Chinese, English and Japanese (include Romaji).
7 Convert synonyms to the standard anime term.

Examples:

校园 -> 学園
school -> 学園

TV -> TV
tv anime -> TV

游戏 -> ゲーム
game -> ゲーム
ゲーム -> ゲーム

监督 -> 監督
director -> 監督

seiyuu -> 声優
voice actor -> 声優
""".strip()

    def __init__(self) -> None:
        if not settings.AI_AGENT_API_KEY:
            raise RuntimeError("AI_AGENT_API_KEY is not configured.")
        self.client = httpx.Client(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.AI_AGENT_API_KEY}",
            },
            timeout=settings.AI_AGENT_TIMEOUT,
        )

    def _request(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": settings.AI_AGENT_MODEL,
            "messages": messages,
        }
        try:
            response = self.client.post(settings.AI_AGENT_API_BASE_URL, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"AI Agent API returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"AI Agent API request failed: {exc}") from exc
        data = response.json()
        try:
            result = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Invalid AI Agent API response: {data}") from exc
        return result.strip() if isinstance(result, str) else ""

    def normalize_name(self, name: str) -> str:
        messages = [
            {"role": "system", "content": self.NAME_SYSTEM_PROMPT},
            {"role": "user", "content": name},
        ]
        return self._request(messages)

    def close(self) -> None:
        self.client.close()


ai_client = AIClient()
