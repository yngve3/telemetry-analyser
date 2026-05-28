"""Snapshot telemetry source adapter."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.snapshot.models import Snapshot
from telemetry_source_backend.domain.snapshot.services import SnapshotCursor


@dataclass(slots=True)
class SnapshotTelemetrySource:
    """Adapter that emits telemetry from uploaded snapshot data."""

    snapshot: Snapshot
    repeat: bool | None = None
    cursor: SnapshotCursor = field(init=False)

    def __post_init__(self) -> None:
        self.cursor = SnapshotCursor(
            samples=self.snapshot.samples,
            repeat=self.snapshot.config.repeat if self.repeat is None else self.repeat,
        )

    async def read(self) -> TelemetrySample | None:
        return self.cursor.next()

    async def stream(self, interval_seconds: float) -> AsyncIterator[TelemetrySample]:
        while sample := self.cursor.next():
            yield sample
            await asyncio.sleep(interval_seconds)
