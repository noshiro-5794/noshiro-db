import httpx

from typing import Any
from django.conf import settings


class BangumiClient:

    def __init__(self) -> None:
        headers = {
            "Accept": "application/json",
            "User-Agent": settings.BANGUMI_USER_AGENT,
        }
        if settings.BANGUMI_API_KEY:
            headers["Authorization"] = f"Bearer {settings.BANGUMI_API_KEY}"
        self.client = httpx.Client(
            base_url=settings.BANGUMI_API_BASE_URL,
            headers=headers,
            timeout=settings.BANGUMI_TIMEOUT,
            follow_redirects=True,
        )

    def _get(self, path: str, **kwargs: Any) -> Any:
        try:
            response = self.client.get(path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Bangumi API returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Bangumi API request failed: {exc}") from exc

    def fetch_calendar(self) -> list:
        return self._get("/calendar")

    def fetch_subject(self, subject_id: int) -> dict:
        return self._get(f"/v0/subjects/{subject_id}")

    def fetch_subject_persons(self, subject_id: int) -> list:
        return self._get(f"/v0/subjects/{subject_id}/persons")

    def fetch_subject_characters(self, subject_id: int) -> list:
        return self._get(f"/v0/subjects/{subject_id}/characters")

    def fetch_subject_subjects(self, subject_id: int) -> list:
        return self._get(f"/v0/subjects/{subject_id}/subjects")

    def fetch_subject_episodes(
        self,
        subject_id: int,
        episode_type: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        params = {"subject_id": subject_id, "limit": limit, "offset": offset}
        if episode_type is not None:
            params["type"] = episode_type
        return self._get("/v0/episodes", params=params)

    def fetch_character(self, character_id: int) -> dict:
        return self._get(f"/v0/characters/{character_id}")

    def fetch_person(self, person_id: int) -> dict:
        return self._get(f"/v0/persons/{person_id}")

    def close(self) -> None:
        self.client.close()


bangumi_client = BangumiClient()
