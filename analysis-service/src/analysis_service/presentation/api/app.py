"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from analysis_service.presentation.api.dependencies import (
    get_cached_ingestion_manager,
)
from analysis_service.presentation.api.routes.detectors import (
    router as detectors_router,
)
from analysis_service.presentation.api.routes.health import router as health_router
from analysis_service.presentation.api.routes.listeners import (
    router as listeners_router,
)
from analysis_service.presentation.api.routes.models import router as models_router
from analysis_service.presentation.api.routes.profile import router as profile_router
from analysis_service.presentation.api.routes.sessions import router as sessions_router
from analysis_service.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        manager = get_cached_ingestion_manager()
        if manager is not None:
            await manager.shutdown()


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title=settings.app_name,
        description="Runtime API for telemetry analysis sessions.",
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(profile_router)
    app.include_router(models_router)
    app.include_router(detectors_router)
    app.include_router(sessions_router)
    app.include_router(listeners_router)
    app.add_exception_handler(
        RequestValidationError,
        _request_validation_exception_handler,
    )
    return app


async def _request_validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    del request
    detail: Any = (
        exc.errors()
        if isinstance(exc, RequestValidationError)
        else str(exc)
    )
    return JSONResponse(
        status_code=400,
        content={"detail": jsonable_encoder(detail)},
    )


app = create_app()
