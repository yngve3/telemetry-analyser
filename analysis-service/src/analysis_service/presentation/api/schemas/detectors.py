"""Detector discovery schemas."""

from pydantic import BaseModel


class DetectorResponse(BaseModel):
    name: str
    kind: str
    status: str
    aliases: list[str]


class DetectorListResponse(BaseModel):
    detectors: list[DetectorResponse]
