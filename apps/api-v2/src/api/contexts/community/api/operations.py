"""Staff-only operations."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import staff_user
from api.contexts.community.campaigns import (
    campaign,
    campaign_claims,
    campaign_items,
    create_campaign,
    list_campaigns,
    summary,
)
from api.contexts.community.import_jobs import (
    create_import_job,
    import_job,
    list_import_jobs,
)
from api.contexts.community.matching import list_candidates
from api.db import SessionDep
from api.shared.cursor import decode, encode
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("/sync/summary/")
async def sync_summary(
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> dict[str, Any]:
    return await summary(session)


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


@router.get("/sync/{campaign_id}/claims/")
async def sync_campaign_claims(
    campaign_id: str,
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(staff_user)],
    status: str = "",
) -> dict[str, Any]:
    page, page_size = page_params(request)
    try:
        data = await campaign_claims(
            session,
            campaign_id=campaign_id,
            status=status,
            page=page,
            page_size=page_size,
        )
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Sync campaign not found.") from error
    if data["count"] == 0 and not data["results"]:
        return data
    return page_payload(
        request,
        count=data["count"],
        results=data["results"],
        page=page,
        page_size=page_size,
    )


@router.get("/sync/")
async def sync_campaigns(
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
    provider: str = "",
    status: str = "",
) -> list[dict[str, Any]]:
    return await list_campaigns(session, provider=provider, status=status)


@router.get("/matching/candidates/")
async def matching_candidates(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(staff_user)],
    status: str = "",
) -> dict[str, Any]:
    page, page_size = page_params(request)
    total, results = await list_candidates(session, status=status, page=page, page_size=page_size)
    ensure_page(page, page_size, total)
    return page_payload(request, count=total, results=results, page=page, page_size=page_size)


@router.get("/import-jobs/")
async def import_job_list(
    session: SessionDep,
    request: Request,
    user: Annotated[Any, Depends(staff_user)],
    provider: str = "",
    status: str = "",
    cursor: str = "",
    page_size: int = 16,
) -> dict[str, Any]:
    try:
        results, next_cursor = await list_import_jobs(
            session,
            viewer_id=user.id,
            provider=provider,
            status=status,
            cursor=decode(cursor or None),
            page_size=min(max(page_size, 1), 64),
        )
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return {
        "next": (
            str(request.url.include_query_params(cursor=encode(next_cursor)))
            if next_cursor is not None
            else None
        ),
        "previous": None,
        "results": results,
    }


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
    return JSONResponse(data, status_code=202)


@router.post("/sync/")
async def create_sync_campaign(
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> JSONResponse:
    try:
        data = await create_campaign(session, body=body)
    except ValueError as error:
        raise ProblemError(
            status_code=400, detail="Request validation failed.", errors=error.args[0]
        ) from error
    return JSONResponse(data, status_code=202)
