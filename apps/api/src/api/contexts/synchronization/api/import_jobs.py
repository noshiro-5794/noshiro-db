"""Staff import job endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import staff_user
from api.contexts.synchronization.import_jobs import (
    ImportDispatchError,
    create_import_job,
    import_job,
    list_import_jobs,
)
from api.db import SessionDep
from api.shared.cursor import decode
from api.shared.pagination import PageSize, cursor_payload
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


@router.get("/import-jobs/")
async def import_job_list(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(staff_user)],
    provider: str = "",
    status: str = "",
    cursor: str = "",
    page_size: PageSize = 16,
) -> dict[str, Any]:
    try:
        results, next_cursor, previous_cursor = await list_import_jobs(
            session,
            viewer_id=user.id,
            provider=provider,
            status=status,
            cursor=decode(cursor or None),
            page_size=page_size,
        )
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return cursor_payload(
        request, results=results, next_cursor=next_cursor, previous_cursor=previous_cursor
    )


@router.post("/import-jobs/")
async def create_job(
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> JSONResponse:
    try:
        data = await create_import_job(session, viewer_id=user.id, body=body)
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    except ImportDispatchError as error:
        raise ProblemError(
            status_code=503, detail=str(error), code="sync.task_dispatch_failed"
        ) from error
    return JSONResponse(data, status_code=202)
