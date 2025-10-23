import os
import requests
from dotenv import load_dotenv
from .exceptions import ExternalAPIError
from typing import Dict, Any, List, Optional


load_dotenv()


class BangumiClient:
    '''
    Client for interacting with the Bangumi API.
    '''

    BASE_URL = "https://api.bgm.tv/v0"
    HEADERS = {
        "Accept": "application/json",
        "Authorization": f"Bearer {os.getenv("BGM_API_TOKEN")}",
        "User-Agent": "Noshiro_5794/noshiro_db (https://github.com/LHYHENRY/noshiro_db_backend)"
    }

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    def search_subject(
            self,
            keyword: str,
            sort: str = "match",
            nsfw: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            type: Optional[List[int]] = None,
            meta_tags: Optional[List[str]] = None,
            tag: Optional[List[str]] = None,
            air_date: Optional[List[str]] = None,
            rating: Optional[List[str]] = None,
            rank: Optional[List[str]] = None,
        ) -> dict:
        url = f"{self.BASE_URL}/search/subject/{keyword}"

    def fetch_subject(self, subject_id: int) -> dict:
        '''
        Fetch subject details by ID.
        '''

        url = f"{self.BASE_URL}/subjects/{subject_id}"

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise ExternalAPIError(f"Failed to fetch Bangumi subject {subject_id}: {e}") from e

    def fetch_subject_persons(self, subject_id: int) -> dict:
        '''
        Fetch persons by ID
        '''

        url = f"{self.BASE_URL}/subjects/{subject_id}/persons"

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise ExternalAPIError(f"Failed to fetch Bangumi subject {subject_id}: {e}") from e

    def fetch_subject_characters(self, subject_id: int) -> dict:
        '''
        Fetch characters by ID
        '''

        url = f"{self.BASE_URL}/subjects/{subject_id}/characters"


class MALClient:
    '''
    Client for interacting with the MyAnimeList API.
    '''

    BASE_URL = "https://api.myanimelist.net/v2"


class JikanClient:
    '''
    Client for interacting with the Jikan API.
    '''

    BASE_URL = "https://api.jikan.moe/v4"


class VNDBClient:
    '''
    Client for interacting with the Visual Novel Database API.
    '''

    BASE_URL = "https://api.vndb.org/kana"
