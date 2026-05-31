"""Analysis model discovery schemas."""

from pydantic import BaseModel


class AnalysisModelResponse(BaseModel):
    name: str
    implementation: str
    status: str
    detector_name: str | None
    connected: bool
    description: str
    aliases: list[str]


class AnalysisModelListResponse(BaseModel):
    models: list[AnalysisModelResponse]


class AnalysisModelProfileResponse(BaseModel):
    name: str
    models: list[str]
    enabled_detectors: list[str]
    status: str
    unavailable_models: list[str]
    description: str


class AnalysisModelProfileListResponse(BaseModel):
    profiles: list[AnalysisModelProfileResponse]
