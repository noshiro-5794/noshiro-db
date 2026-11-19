from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from .config import settings
from .contexts.access.api.logout import router as logout_router
from .contexts.access.api.profile import router as profile_router
from .contexts.access.api.profiles import router as profiles_router
from .contexts.access.api.refresh import router as refresh_router
from .contexts.access.api.registration import router as registration_router
from .contexts.access.api.session import router as session_router
from .contexts.access.api.settings import router as settings_router
from .contexts.access.api.social import router as social_router
from .contexts.community.api.blocks import router as community_blocks_router
from .contexts.community.api.notifications import (
    router as community_notifications_router,
)
from .contexts.community.api.operations import router as operations_router
from .contexts.library.api.collections import router as collections_router
from .contexts.library.api.entries import router as library_entries_router
from .contexts.library.api.progress import router as progress_router
from .contexts.library.api.public import router as public_library_router
from .contexts.library.api.reviews import router as reviews_router
from .contexts.library.api.stats import router as library_stats_router
from .contexts.library.api.tags import router as library_tags_router
from .contexts.presentation.api.board import router as board_router
from .contexts.presentation.api.calendar import router as calendar_router
from .contexts.presentation.api.catalogue import router as catalogue_router
from .contexts.presentation.api.entity import router as entity_router
from .contexts.presentation.api.health import router as health_router
from .contexts.signal.api import router as signal_router
from .shared.problems import ProblemError, http_error_handler, problem_handler, validation_handler
from .shared.schema import Application


def create_app() -> FastAPI:
    app = Application(
        title="Noshiro API",
        version="0.1.0",
        openapi_url="/api/v1/openapi/",
        docs_url="/api/v1/docs/",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.cors_allow_all_origins else settings.cors_allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"],
        allow_headers=[
            "accept",
            "authorization",
            "content-type",
            "user-agent",
            "x-csrftoken",
            "x-requested-with",
        ],
    )
    app.include_router(health_router)
    app.include_router(registration_router)
    app.include_router(social_router)
    app.include_router(session_router)
    app.include_router(refresh_router)
    app.include_router(profile_router)
    app.include_router(collections_router)
    app.include_router(profiles_router)
    app.include_router(library_tags_router)
    app.include_router(library_stats_router)
    app.include_router(library_entries_router)
    app.include_router(progress_router)
    app.include_router(reviews_router)
    app.include_router(public_library_router)
    app.include_router(logout_router)
    app.include_router(settings_router)
    app.include_router(catalogue_router)
    app.include_router(calendar_router)
    app.include_router(board_router)
    app.include_router(community_notifications_router)
    app.include_router(community_blocks_router)
    app.include_router(operations_router)
    app.include_router(entity_router)
    app.include_router(signal_router)
    app.add_exception_handler(ProblemError, problem_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    return app


app = create_app()
