"""HTTP operations for finished episodes in the user's library."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from api.contexts.access.dependencies import current_user
from api.contexts.library.progress import (
    clear_finished,
    get_progress,
    replace_progress,
    set_finished,
)
from api.db import SessionDep
from api.shared.problems import ProblemError

from .schemas import EpisodeProgressReplace

router = APIRouter(prefix="/api/v1/users/me/library/entries", tags=["library"])


@router.get("/{entry_id}/episodes/progress/")
async def progress(
    entry_id: int, session: SessionDep, user: Annotated[Any, Depends(current_user)]
) -> dict[str, Any]:
    try:
        return await get_progress(session, user_id=user.id, entry_id=entry_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error


@router.put("/{entry_id}/episodes/progress/")
async def replace(
    entry_id: int,
    body: EpisodeProgressReplace,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await replace_progress(
            session, user_id=user.id, entry_id=entry_id, finished=body.finished_episode_ids
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error


@router.put("/{entry_id}/episodes/{episode_id}/progress/")
async def finish(
    entry_id: int,
    episode_id: UUID,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> dict[str, Any]:
    try:
        return await set_finished(
            session, user_id=user.id, entry_id=entry_id, episode_id=episode_id
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error
    except FileNotFoundError as error:
        raise ProblemError(status_code=404, detail="Episode not found for this Work.") from error


@router.delete("/{entry_id}/episodes/{episode_id}/progress/", status_code=204)
async def unfinish(
    entry_id: int,
    episode_id: UUID,
    session: SessionDep,
    user: Annotated[Any, Depends(current_user)],
) -> None:
    try:
        await clear_finished(session, user_id=user.id, entry_id=entry_id, episode_id=episode_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Library entry not found.") from error
