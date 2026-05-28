"""Use case for publishing one telemetry sample."""

from dataclasses import dataclass

from telemetry_source_backend.application.ports import (
    TelemetryEncoder,
    TelemetrySource,
    TelemetryTransport,
)


@dataclass(frozen=True, slots=True)
class PublishOnce:
    source: TelemetrySource
    encoder: TelemetryEncoder
    transport: TelemetryTransport

    async def execute(self) -> None:
        sample = await self.source.read()
        payload = self.encoder.encode(sample)
        await self.transport.send(payload)

