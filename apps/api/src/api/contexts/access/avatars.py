"""Validate avatar images and replace their stored profile reference."""

import asyncio
import logging
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.contexts.presentation.fragments import fetch
from api.integrations.storage import ObjectStorage
from api.shared.problems import ProblemError

from .profiles import get_or_create_profile

logger = logging.getLogger(__name__)
STORAGE_ERRORS = (BotoCoreError, ClientError, ValueError)
INVALID_IMAGE = (
    "Upload a valid image. The file you uploaded was either not an image or a corrupted image."
)


def validate_avatar(data: bytes, filename: str) -> tuple[str, str]:
    message = ""
    if not data:
        message = "The submitted file is empty."
    elif len(data) > settings.avatar_max_upload_size:
        size = settings.avatar_max_upload_size / 1024 / 1024
        message = f"Avatar file size must be less than or equal to {size:.0f}MB."
    if message:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors={"avatar": [message]}
        )
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
            image_format = image.format
            content_type = Image.MIME.get(image_format or "", "").lower()
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors={"avatar": [INVALID_IMAGE]}
        ) from error
    extensions = Image.registered_extensions()
    suffix = Path(filename).suffix.lower()
    if suffix not in extensions:
        allowed = ", ".join(extension[1:] for extension in extensions)
        message = (
            f"File extension “{suffix[1:]}” is not allowed. Allowed extensions are: {allowed}."
        )
    elif content_type not in settings.avatar_allowed_content_types:
        allowed = ", ".join(settings.avatar_allowed_content_types)
        message = f"Unsupported avatar content type. Allowed: {allowed}."
    if message:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors={"avatar": [message]}
        )
    extension = next(
        (value for value, format_name in extensions.items() if format_name == image_format), suffix
    )
    return content_type, ".jpg" if image_format == "JPEG" else extension


async def _discard(storage: ObjectStorage, url: str, user_id: int) -> None:
    try:
        await asyncio.to_thread(storage.delete_public_url, url, prefix=f"avatars/{user_id}/")
    except STORAGE_ERRORS:
        logger.warning("Avatar object cleanup failed", extra={"user_id": user_id}, exc_info=True)


async def upload_avatar(
    session: AsyncSession, *, user_id: int, data: bytes, filename: str, storage: ObjectStorage
) -> str:
    content_type, extension = await asyncio.to_thread(validate_avatar, data, filename)
    await get_or_create_profile(session, user_id=user_id)
    await session.commit()
    name = f"avatars/{user_id}/{uuid4().hex}{extension}"
    try:
        url = await asyncio.to_thread(storage.upload_bytes, name, data, content_type)
    except STORAGE_ERRORS as error:
        raise ProblemError(
            status_code=502,
            detail="The avatar could not be uploaded.",
            code="users.avatar_upload_failed",
        ) from error
    try:
        rows = await fetch(
            session,
            "SELECT avatar FROM user_profile WHERE user_id=:user FOR UPDATE",
            {"user": user_id},
        )
        if not rows:
            raise LookupError(user_id)
        old_url = rows[0].avatar
        await fetch(
            session,
            "UPDATE user_profile SET avatar=:url WHERE user_id=:user RETURNING user_id",
            {"url": url, "user": user_id},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        # A lost commit response can leave a durable reference. Keep the object
        # whenever that outcome cannot be verified, avoiding a dangling avatar.
        referenced = True
        try:
            current = await fetch(
                session, "SELECT avatar FROM user_profile WHERE user_id=:user", {"user": user_id}
            )
            referenced = bool(current and current[0].avatar == url)
        except Exception:
            logger.warning(
                "Avatar reference could not be checked after a failed write",
                extra={"user_id": user_id},
                exc_info=True,
            )
        finally:
            await session.rollback()
        if not referenced:
            await _discard(storage, url, user_id)
        raise
    if old_url and old_url != url:
        await _discard(storage, old_url, user_id)
    return url
