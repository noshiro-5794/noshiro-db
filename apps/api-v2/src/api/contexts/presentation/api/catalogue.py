from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session

router = APIRouter(prefix="/api/v1/index", tags=["catalogue"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/collections/")
async def collections(session: SessionDep) -> list[dict[str, str]]:
    rows = (
        await session.execute(
            text("SELECT slug, name FROM curated_collection WHERE is_enabled ORDER BY id")
        )
    ).all()
    return [{"slug": row.slug, "name": row.name} for row in rows]
