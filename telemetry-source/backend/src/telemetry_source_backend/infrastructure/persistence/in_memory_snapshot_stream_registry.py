"""In-memory registry for snapshot UDP streams."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from telemetry_source_backend.domain.common.models import TelemetrySample

PREVIEW_SAMPLE_LIMIT = 10


@dataclass(slots=True)
class SnapshotUdpStreamRecord:
    """Runtime state for snapshot UDP replay."""

    snapshot_id: str
    host: str
    port: int
    frequency_hz: float
    repeat: bool = False
    stream_id: str = field(default_factory=lambda: str(uuid4()))
    is_active: bool = False
    samples_sent: int = 0
    frames_sent: int = 0
    preview_samples: list[TelemetrySample] = field(default_factory=list)
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task[None] | None = None

    def remember_sample(self, sample: TelemetrySample) -> None:
        self.preview_samples.append(sample)
        if len(self.preview_samples) > PREVIEW_SAMPLE_LIMIT:
            del self.preview_samples[:-PREVIEW_SAMPLE_LIMIT]


class InMemorySnapshotStreamRegistry:
    """Stores snapshot stream tasks for the backend process lifetime."""

    def __init__(self) -> None:
        self._records: dict[str, SnapshotUdpStreamRecord] = {}

    def save(self, record: SnapshotUdpStreamRecord) -> None:
        self._records[record.stream_id] = record

    def get(self, stream_id: str) -> SnapshotUdpStreamRecord | None:
        return self._records.get(stream_id)

    def list(self) -> list[SnapshotUdpStreamRecord]:
        return list(self._records.values())
