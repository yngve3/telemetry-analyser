"""Analysis session API schemas."""

from __future__ import annotations

from pydantic import BaseModel
from typing import Any

from analysis_service.application import AnalysisSession
from analysis_service.presentation.api.schemas.profiles import (
    AnalysisProfileRequest,
    AnalysisProfileResponse,
)


class AnalysisSessionCreateRequest(BaseModel):
    session_id: str | None = None
    drone_id: str | None = None
    profile: AnalysisProfileRequest | None = None


class AnalysisSessionResponse(BaseModel):
    session_id: str
    drone_id: str | None = None
    created_at: str
    last_analyzed_at: str | None = None
    samples_analyzed: int
    profile: AnalysisProfileResponse

    @classmethod
    def from_session(cls, session: AnalysisSession) -> "AnalysisSessionResponse":
        return cls(**session.to_dict())


class AnalysisSessionDeletedResponse(BaseModel):
    session_id: str
    deleted: bool


class AnalysisSessionLastResultResponse(BaseModel):
    session_id: str
    result: dict[str, Any] | None = None


class AnalysisSessionLastTelemetryResponse(BaseModel):
    session_id: str
    telemetry: dict[str, Any] | None = None


class AnalysisSessionStateResponse(BaseModel):
    session: AnalysisSessionResponse
    last_telemetry: dict[str, Any] | None = None
    last_result: dict[str, Any] | None = None
