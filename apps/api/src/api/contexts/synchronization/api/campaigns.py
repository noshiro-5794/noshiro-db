"""Synchronization campaign administration."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import staff_user
from api.contexts.synchronization.campaign_admin import (
    campaign,
    campaign_claims,
    campaign_items,
    create_campaign,
    list_campaigns,
    summary,
)
from api.db import SessionDep
from api.shared.dispatch import DispatchUnavailable
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("/sync/summary/")
async def sync_summary(
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> dict[str, Any]:
    return await summary(session)


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
    except DispatchUnavailable as error:
        raise ProblemError(
            status_code=503, detail=str(error), code="sync.task_dispatch_failed"
        ) from error
    return JSONResponse(data, status_code=202)


@router.post("/sync/{campaign_id}/{action}/")
async def control_campaign(
    campaign_id: str,
    action: str,
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> dict[str, Any]:
    from api.contexts.synchronization.campaigns import control
    from api.contexts.synchronization.domain import UnsupportedAction
    from api.shared.dispatch import SYNC_TASK, enqueue, sync_kwargs

    try:
        updated = await control(session, campaign_id, action)
    except UnsupportedAction as error:
        raise ProblemError(status_code=404, detail="Unsupported campaign action.") from error
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Sync campaign not found.") from error
    await session.commit()
    if action == "resume" and updated.status not in {"paused", "cancelled"}:
        try:
            await enqueue(SYNC_TASK, sync_kwargs(campaign_id=str(updated.id)))
        except DispatchUnavailable as error:
            raise ProblemError(
                status_code=503, detail=str(error), code="sync.task_dispatch_failed"
            ) from error
    return await campaign(session, campaign_id=str(updated.id))
