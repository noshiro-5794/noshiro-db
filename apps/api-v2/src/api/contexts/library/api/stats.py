"""The signed-in user's yearly library statistics."""

from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends

from api.contexts.access.dependencies import current_user
from api.contexts.library.stats import stats
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/users", tags=["library"])


@router.get("/me/profile/stats/")
async def my_stats(
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
    year: int = 0,
    timezone: str = "UTC",
) -> dict[str, Any]:
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors={"timezone": ["Unknown IANA timezone."]},
        ) from error
    current = datetime.now(zone).year
    chosen = year or current
    if chosen > current + 1:
        raise ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors={"year": [f"Year must be less than or equal to {current + 1}."]},
        )
    return await stats(session, user_id=user.id, year=chosen, zone=zone)
