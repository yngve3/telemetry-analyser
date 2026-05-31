"""Detector discovery schemas."""

from pydantic import BaseModel


class DetectorResponse(BaseModel):
    name: str
    implementation: str
    status: str
    detector_name: str | None
    connected: bool
    description: str
    aliases: list[str]


class DetectorListResponse(BaseModel):
    detectors: list[DetectorResponse]
