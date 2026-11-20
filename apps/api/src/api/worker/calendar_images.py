"""Bounded calendar-cover downloads to the configured S3-compatible store."""

import logging
import os
from pathlib import PurePosixPath
from urllib.parse import urlparse

import httpx

from api.integrations.storage import ObjectStorage
from api.worker.providers.http import client as build_client

logger = logging.getLogger(__name__)


def image_url(images: object) -> str:
    if not isinstance(images, dict):
        return ""
    for key in ("large", "common", "medium", "grid", "small"):
        value = images.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def allowed_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not host:
        return False
    allowed = os.environ.get("BANGUMI_IMAGE_ALLOWED_HOSTS", "lain.bgm.tv")
    hosts = {entry.strip().lower() for entry in allowed.split(",")}
    hosts.discard("")
    return any(host == candidate or host.endswith("." + candidate) for candidate in hosts)


def extension(url: str, content_type: str) -> str:
    known = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if content_type in known:
        return known[content_type]
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


class CalendarImages:
    def __init__(
        self, *, http: httpx.Client | None = None, storage: ObjectStorage | None = None
    ) -> None:
        self._http = http
        self.storage = storage or ObjectStorage()

    def cache_cover(self, subject_id: int, images: object) -> str:
        url = image_url(images)
        if not url or not allowed_url(url):
            return ""
        try:
            if self._http is None:
                self._http = build_client(base_url=url, headers={"User-Agent": "noshiro-db"})
            maximum = int(os.environ.get("BANGUMI_IMAGE_MAX_BYTES", str(10 * 1024 * 1024)))
            with self._http.stream("GET", url) as response:
                response.raise_for_status()
                content_type = (
                    response.headers.get("content-type", "").split(";")[0].strip().lower()
                )
                if content_type and not content_type.startswith("image/"):
                    return ""
                length = response.headers.get("content-length", "")
                if length.isdigit() and int(length) > maximum:
                    return ""
                data = bytearray()
                for chunk in response.iter_bytes():
                    if len(data) + len(chunk) > maximum:
                        return ""
                    data.extend(chunk)
            name = f"calendar-covers/{subject_id}{extension(url, content_type)}"
            return self.storage.upload_bytes(name, bytes(data), content_type or "image/jpeg")
        except Exception:
            logger.warning(
                "Calendar cover caching failed", extra={"subject_id": subject_id}, exc_info=True
            )
            return ""

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None
        self.storage.close()
