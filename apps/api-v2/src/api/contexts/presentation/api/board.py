from typing import Any

from fastapi import APIRouter

from api.contexts.presentation.board import board_entries
from api.db import SessionDep

router = APIRouter(prefix="/api/v1/index", tags=["calendar"])


@router.get("/calendar/board/events/")
async def board(session: SessionDep, include_work: str = "") -> list[dict[str, Any]]:
    return await board_entries(session, include_work=include_work.lower() in {"1", "true", "yes"})
