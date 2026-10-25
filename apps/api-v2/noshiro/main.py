from fastapi import FastAPI

from .contexts.presentation.api.health import router as health_router
from .contexts.signal.api import router as signal_router


def create_app() -> FastAPI:
    app = FastAPI(title="Noshiro API", version="0.1.0")
    app.include_router(health_router)
    app.include_router(signal_router)
    return app


app = create_app()
