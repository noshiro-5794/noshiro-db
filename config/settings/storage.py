import os
from urllib.parse import urlparse


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _normalize_minio_endpoint(value: str | None) -> tuple[str | None, bool | None]:
    if not value:
        return None, None

    endpoint = value.strip().rstrip("/")
    parsed = urlparse(endpoint)

    if parsed.scheme in {"http", "https"}:
        return parsed.netloc, parsed.scheme == "https"

    return endpoint, None


MINIO_ENDPOINT_RAW = os.getenv("MINIO_ENDPOINT")

MINIO_ENDPOINT, MINIO_ENDPOINT_USES_HTTPS = _normalize_minio_endpoint(
    MINIO_ENDPOINT_RAW
)

MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")

MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

MINIO_USE_HTTPS = (
    MINIO_ENDPOINT_USES_HTTPS
    if MINIO_ENDPOINT_USES_HTTPS is not None
    else _parse_bool(os.getenv("MINIO_USE_HTTPS"))
)

MINIO_BUCKET = os.getenv("MINIO_BUCKET")

MINIO_PUBLIC_URL = (
    os.getenv("MINIO_PUBLIC_URL")
    or (
        f"{'https' if MINIO_USE_HTTPS else 'http'}://{MINIO_ENDPOINT}"
        if MINIO_ENDPOINT
        else None
    )
)

AVATAR_MAX_UPLOAD_SIZE = int(
    os.getenv("AVATAR_MAX_UPLOAD_SIZE", str(10 * 1024 * 1024))
)

AVATAR_ALLOWED_CONTENT_TYPES = [
    content_type.strip().lower()
    for content_type in os.getenv(
        "AVATAR_ALLOWED_CONTENT_TYPES",
        "image/jpeg,image/png,image/webp",
    ).split(",")
    if content_type.strip()
]
