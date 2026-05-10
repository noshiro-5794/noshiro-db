import os
import httpx

from dotenv import load_dotenv


load_dotenv()


class BangumiClient:

    BASE_URL = "https://api.bgm.tv"

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {os.getenv('BGM_API_KEY')}",
                "User-Agent": "Noshiro_5794/noshiro_db (https://github.com/LHYHENRY/noshiro_db_backend)",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    def fetch_calendar(self) -> dict:
        url = f"{self.BASE_URL}/calendar"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Bangumi fetch_calendar failed: {e}") from e

    def fetch_subject(self, subject_id: int) -> dict:
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Bangumi fetch_subject failed: {e}") from e

    def fetch_subject_persons(self, subject_id: int) -> list:
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}/persons"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Bangumi fetch_subject_persons failed: {e}") from e

    def fetch_subject_characters(self, subject_id: int) -> list:
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}/characters"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Bangumi fetch_subject_characters failed: {e}") from e

    def fetch_subject_subjects(self, subject_id: int) -> list:
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}/subjects"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Bangumi fetch_subject_subjects failed: {e}") from e

    def fetch_subject_episodes(
        self, subject_id: int, type: int = None, limit: int = 100, offset: int = 0
    ) -> dict:
        url = f"{self.BASE_URL}/v0/episodes"
        params = {"subject_id": subject_id, "limit": limit, "offset": offset}
        if type is not None:
            params["type"] = type
        try:
            resp = self.client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Bangumi fetch_subject_episodes failed: {e}") from e

    def fetch_character(self, character_id: int) -> dict:
        url = f"{self.BASE_URL}/v0/characters/{character_id}"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Bangumi fetch_character failed: {e}") from e

    def fetch_person(self, person_id: int) -> dict:
        url = f"{self.BASE_URL}/v0/persons/{person_id}"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Bangumi fetch_person failed: {e}") from e


bangumi_client = BangumiClient()
