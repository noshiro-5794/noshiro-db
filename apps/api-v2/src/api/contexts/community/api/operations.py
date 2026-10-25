"""Staff-only operations."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from api.contexts.access.dependencies import staff_user
from api.contexts.community.import_jobs import import_job
from api.db import SessionDep
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("/import-jobs/{job_id}/")
async def import_job_detail(
    job_id: str,
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> dict[str, Any]:
    try:
        return await import_job(session, job_id=job_id)
    except KeyError as error:
        raise ProblemError(status_code=404, detail="Import job not found.") from error
    except LookupError as error:
        raise ProblemError(
            status_code=404,
            detail="Synchronization job not found.",
            code="sync.job_not_found",
        ) from error
