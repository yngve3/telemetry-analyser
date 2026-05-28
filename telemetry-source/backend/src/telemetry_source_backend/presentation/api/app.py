"""FastAPI application factory."""

from fastapi import FastAPI

from telemetry_source_backend.presentation.api.routes.external import (
    router as external_router,
)
from telemetry_source_backend.presentation.api.routes.health import router as health_router
from telemetry_source_backend.presentation.api.routes.snapshots import (
    router as snapshots_router,
)
from telemetry_source_backend.presentation.api.routes.sources import router as sources_router
from telemetry_source_backend.presentation.api.routes.streaming import router as streaming_router
from telemetry_source_backend.presentation.api.routes.translations import (
    router as translations_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telemetry Source",
        description="Backend API for configuring telemetry sources and running synthetic missions.",
        version="0.1.0",
    )
    app.include_router(health_router)
    app.include_router(sources_router)
    app.include_router(snapshots_router)
    app.include_router(external_router)
    app.include_router(streaming_router)
    app.include_router(translations_router)
    return app


app = create_app()
