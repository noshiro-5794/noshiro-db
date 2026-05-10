import os
import httpx

from dotenv import load_dotenv


load_dotenv()


class AIClient:

    BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
    MODEL = "Pro/zai-org/GLM-4.7"

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
"""

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('SILICONFLOW_API_KEY')}",
            },
            timeout=30.0,
        )

    def _request(self, messages) -> str:
        payload = {"model": self.MODEL, "messages": messages}
        resp = self.client.post(self.BASE_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        result = data["choices"][0]["message"]["content"]
        return result.strip() if isinstance(result, str) else ""

    def normalize_name(self, name: str) -> str:
        messages = [
            {"role": "system", "content": self.NAME_SYSTEM_PROMPT},
            {"role": "user", "content": name},
        ]
        return self._request(messages)


ai_client = AIClient()
