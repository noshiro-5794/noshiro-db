from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ....db import ping

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live/")
async def live() -> JSONResponse:
    return _response()


@router.get("/ready/")
async def ready() -> JSONResponse:
    try:
        await ping()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from error
    return _response()


def _response(status_code: int = 200) -> JSONResponse:
    """Same body as the old service, and the same Cache-Control."""
    response = JSONResponse({"status": "ok"}, status_code=status_code)
    response.headers["Cache-Control"] = "no-store"
    return response
