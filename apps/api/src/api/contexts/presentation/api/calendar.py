from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Header, Query

from api.contexts.presentation.calendar import calendar_events
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/index", tags=["calendar"])


def _parse(name: str, value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProblemError(status_code=400, detail=f"Invalid {name}.") from error


@router.get("/calendar/events/")
async def calendar(
    session: SessionDep,
    start: Annotated[str | None, Query(alias="from")] = None,
    end: Annotated[str | None, Query(alias="to")] = None,
    timezone: str = "",
    include_work: str = "",
    accept_language: Annotated[str | None, Header()] = None,
) -> list[dict[str, Any]]:
    del accept_language
    return await calendar_events(
        session,
        start=_parse("from", start),
        end=_parse("to", end),
        timezone=timezone,
        include_work=include_work.lower() in {"1", "true", "yes"},
    )
