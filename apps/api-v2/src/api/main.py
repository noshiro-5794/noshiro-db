from fastapi import FastAPI

from .contexts.access.api.social import router as social_router
from .contexts.presentation.api.calendar import router as calendar_router
from .contexts.presentation.api.catalogue import router as catalogue_router
from .contexts.presentation.api.entity import router as entity_router
from .contexts.presentation.api.health import router as health_router
from .contexts.signal.api import router as signal_router
from .shared.problems import ProblemError, problem_handler


def create_app() -> FastAPI:
    app = FastAPI(title="Noshiro API", version="0.1.0")
    app.include_router(health_router)
    app.include_router(social_router)
    app.include_router(catalogue_router)
    app.include_router(calendar_router)
    app.include_router(entity_router)
    app.include_router(signal_router)
    app.add_exception_handler(ProblemError, problem_handler)
    return app


app = create_app()
