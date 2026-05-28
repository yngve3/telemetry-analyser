"""Snapshot source API response schemas."""

from pydantic import BaseModel

from telemetry_source_backend.presentation.api.schemas.synthetic_responses import (
    TelemetrySampleResponse,
)


class SnapshotStatusResponse(BaseModel):
    snapshot_id: str
    name: str
    samples_count: int
    interval_seconds: float
    repeat: bool


class SnapshotCreatedResponse(BaseModel):
    snapshot_id: str
    status: SnapshotStatusResponse


class SnapshotListItemResponse(BaseModel):
    snapshot_id: str
    name: str
    samples_count: int


class SnapshotSendOnceResponse(BaseModel):
    snapshot_id: str
    host: str
    port: int
    samples_sent: int
    frames_sent: int


class SnapshotUdpStreamStatusResponse(BaseModel):
    stream_id: str
    snapshot_id: str
    host: str
    port: int
    frequency_hz: float
    repeat: bool
    is_active: bool
    samples_sent: int
    frames_sent: int


class SnapshotSamplesResponse(BaseModel):
    snapshot_id: str
    samples: list[TelemetrySampleResponse]
