from fastapi import APIRouter
from sqlalchemy import text

from api.db import SessionDep

router = APIRouter(prefix="/api/v1/index", tags=["catalogue"])


@router.get("/collections/")
async def collections(session: SessionDep) -> list[dict[str, str]]:
    rows = (
        await session.execute(
            text("SELECT slug, name FROM curated_collection WHERE is_enabled ORDER BY id")
        )
    ).all()
    return [{"slug": row.slug, "name": row.name} for row in rows]
