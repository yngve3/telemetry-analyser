"""In-memory registry for synthetic UDP streams."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from telemetry_source_backend.domain.common.models import TelemetrySample

PREVIEW_SAMPLE_LIMIT = 10


@dataclass(slots=True)
class SyntheticUdpStreamRecord:
    """Runtime state for a UDP publication stream."""

    mission_id: str
    host: str
    port: int
    frequency_hz: float
    stream_id: str = field(default_factory=lambda: str(uuid4()))
    is_active: bool = False
    sent_count: int = 0
    preview_samples: list[TelemetrySample] = field(default_factory=list)
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task[None] | None = None

    def remember_sample(self, sample: TelemetrySample) -> None:
        self.preview_samples.append(sample)
        if len(self.preview_samples) > PREVIEW_SAMPLE_LIMIT:
            del self.preview_samples[:-PREVIEW_SAMPLE_LIMIT]


class InMemorySyntheticStreamRegistry:
    """Stores active synthetic stream tasks for the backend process lifetime."""

    def __init__(self) -> None:
        self._records: dict[str, SyntheticUdpStreamRecord] = {}

    def save(self, record: SyntheticUdpStreamRecord) -> None:
        self._records[record.stream_id] = record

    def get(self, stream_id: str) -> SyntheticUdpStreamRecord | None:
        return self._records.get(stream_id)

    def list(self) -> list[SyntheticUdpStreamRecord]:
        return list(self._records.values())
