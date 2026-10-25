"""Staff-only operations."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from api.contexts.access.dependencies import staff_user
from api.contexts.community.campaigns import campaign, campaign_items
from api.contexts.community.import_jobs import import_job
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
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


@router.get("/sync/{campaign_id}/")
async def sync_campaign(
    campaign_id: str,
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> dict[str, Any]:
    try:
        return await campaign(session, campaign_id=campaign_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Sync campaign not found.") from error


@router.get("/sync/{campaign_id}/items/")
async def sync_campaign_items(
    campaign_id: str,
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(staff_user)],
    status: str = "",
) -> dict[str, Any]:
    page, page_size = page_params(request)
    try:
        total, results = await campaign_items(
            session,
            campaign_id=campaign_id,
            status=status,
            page=page,
            page_size=page_size,
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Sync campaign not found.") from error
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)
