"""Multipart avatar uploads for the signed-in account."""

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BeforeValidator
from pydantic_core import PydanticCustomError
from starlette.datastructures import UploadFile as UploadedFile

from api.config import settings
from api.contexts.access.avatars import upload_avatar
from api.contexts.access.dependencies import current_user
from api.db import SessionDep
from api.integrations.storage import ObjectStorage
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/users", tags=["profile"])


def _uploaded_file(value: Any) -> Any:
    if not isinstance(value, UploadedFile):
        raise PydanticCustomError(
            "file_type", "The submitted data was not a file. Check the encoding type on the form."
        )
    return value


async def avatar_storage() -> AsyncIterator[ObjectStorage]:
    storage = ObjectStorage()
    try:
        yield storage
    finally:
        await asyncio.to_thread(storage.close)


async def _form_user(request: Request, user: Annotated[Any, Depends(current_user)]) -> Any:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
    if content_type and content_type.lower() not in {
        "multipart/form-data",
        "application/x-www-form-urlencoded",
    }:
        raise ProblemError(
            status_code=415, detail=f'Unsupported media type "{content_type}" in request.'
        )
    if "avatar" not in await request.form():
        raise ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors={"avatar": ["No file was submitted."]},
        )
    return user


@router.post("/me/avatar/")
async def avatar(
    avatar: Annotated[UploadFile, File(), BeforeValidator(_uploaded_file)],
    session: SessionDep,
    user: Annotated[Any, Depends(_form_user)],
    storage: Annotated[ObjectStorage, Depends(avatar_storage)],
) -> dict[str, str]:
    data = await avatar.read(settings.avatar_max_upload_size + 1)
    url = await upload_avatar(
        session, user_id=user.id, data=data, filename=avatar.filename or "", storage=storage
    )
    return {"avatar": url}
