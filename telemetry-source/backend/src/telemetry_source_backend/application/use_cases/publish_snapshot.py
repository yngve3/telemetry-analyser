"""Snapshot publication use cases."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from telemetry_source_backend.application.ports import (
    TelemetryFrameEncoder,
    TelemetryTransport,
    TelemetryValidator,
)
from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.snapshot.models import Snapshot
from telemetry_source_backend.domain.snapshot.services import SnapshotCursor


@dataclass(frozen=True, slots=True)
class SnapshotPublicationResult:
    """Counters produced by snapshot publication."""

    samples_sent: int
    frames_sent: int


@dataclass(frozen=True, slots=True)
class SnapshotUdpPublisher:
    """Publishes snapshot telemetry through an injected UDP pipeline."""

    encoder: TelemetryFrameEncoder
    transport: TelemetryTransport
    validator: TelemetryValidator

    async def send_once(
        self,
        samples: Sequence[TelemetrySample],
    ) -> SnapshotPublicationResult:
        samples_sent = 0
        frames_sent = 0
        for sample in samples:
            frames_sent += await self._publish_sample(sample)
            samples_sent += 1

        return SnapshotPublicationResult(
            samples_sent=samples_sent,
            frames_sent=frames_sent,
        )

    async def replay(
        self,
        snapshot: Snapshot,
        interval_seconds: float,
        repeat: bool,
        stop_event: asyncio.Event,
        on_sample_sent: Callable[[int], None],
        on_sample_ready: Callable[[TelemetrySample], None] | None = None,
    ) -> None:
        cursor = SnapshotCursor(samples=snapshot.samples, repeat=repeat)
        while not stop_event.is_set():
            sample = cursor.next()
            if sample is None:
                return

            if on_sample_ready is not None:
                on_sample_ready(sample)
            frames_sent = await self._publish_sample(sample)
            on_sample_sent(frames_sent)
            await asyncio.sleep(interval_seconds)

    async def _publish_sample(self, sample: TelemetrySample) -> int:
        self.validator.validate_sample(sample)
        frames_sent = 0
        for frame in self.encoder.encode_messages(sample):
            await self.transport.send(frame)
            frames_sent += 1

        return frames_sent
