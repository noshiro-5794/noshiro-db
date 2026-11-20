"""Staff match review and decision endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.contexts.access.dependencies import staff_user
from api.contexts.matching.read_models import list_candidates
from api.db import SessionDep
from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


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


@router.post("/matching/candidates/{candidate_id}/decide/")
async def decide_candidate(
    candidate_id: str,
    body: dict[str, Any],
    session: SessionDep,
    user: Annotated[Any, Depends(staff_user)],
) -> JSONResponse:
    """Record the decision and answer with the candidate as it was read.

    The old service serialises the object it loaded before deciding, so a successful
    decide answers `pending`. That is a bug, but it is the contract clients see, and
    the port reproduces it rather than quietly changing the shape.
    """
    from api.contexts.index import resolution
    from api.contexts.matching.read_models import candidate_by_id

    try:
        payload = await candidate_by_id(session, viewer_id=user.id, candidate_id=candidate_id)
    except LookupError as error:
        raise ProblemError(status_code=404, detail="Match candidate not found.") from error
    outcome = body.get("outcome")
    if outcome not in {"bind", "group", "reject", "abstain"}:
        raise ProblemError(
            status_code=400,
            detail="Request validation failed.",
            errors={"outcome": [f'"{outcome}" is not a valid choice.']},
        )
    reason = str(body.get("reason") or "")
    try:
        await resolution.decide(
            session,
            candidate_id=candidate_id,
            outcome=str(outcome),
            reason=reason,
        )
        if outcome == "group":
            candidate = await resolution.candidate_entities(session, candidate_id)
            await resolution.ensure_pair_group(
                session,
                left_id=candidate.left_entity_id,
                right_id=candidate.right_entity_id,
                reason=reason or "admin-group",
            )
        await resolution.settle_proposal(
            session,
            candidate_id=candidate_id,
            accepted=outcome in {"bind", "group"},
            reason=reason,
            grouped=outcome == "group",
        )
        await session.commit()
    except resolution.CandidateNotFound as error:
        raise ProblemError(status_code=404, detail="Match candidate not found.") from error
    except resolution.ResolutionError as error:
        raise ProblemError(status_code=409, detail=str(error)) from error
    return JSONResponse(payload)
