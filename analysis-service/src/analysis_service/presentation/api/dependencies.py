"""FastAPI dependency providers."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from analysis_service.application import IngestionManager, SessionManager
from analysis_service.infrastructure.listeners import UdpMavlinkListener
from analysis_service.validation import JsonSchemaTelemetryValidator


@lru_cache(maxsize=1)
def get_session_manager() -> SessionManager:
    return SessionManager()


@lru_cache(maxsize=1)
def get_telemetry_schema_validator() -> JsonSchemaTelemetryValidator:
    return JsonSchemaTelemetryValidator.load_default()


_ingestion_manager: IngestionManager | None = None


def get_ingestion_manager(
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> IngestionManager:
    global _ingestion_manager
    if _ingestion_manager is None:
        _ingestion_manager = IngestionManager(
            session_manager=session_manager,
            listener_factory=lambda _: UdpMavlinkListener(),
        )
    return _ingestion_manager


def reset_ingestion_manager() -> None:
    global _ingestion_manager
    _ingestion_manager = None


def get_cached_ingestion_manager() -> IngestionManager | None:
    return _ingestion_manager


SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]
IngestionManagerDep = Annotated[IngestionManager, Depends(get_ingestion_manager)]
TelemetrySchemaValidatorDep = Annotated[
    JsonSchemaTelemetryValidator,
    Depends(get_telemetry_schema_validator),
]
