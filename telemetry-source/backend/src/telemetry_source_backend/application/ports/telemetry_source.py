"""Telemetry source port."""

from typing import AsyncIterator, Protocol

from telemetry_source_backend.domain.common.models import TelemetrySample


class TelemetrySource(Protocol):
    """Port for components that produce telemetry samples."""

    async def read(self) -> TelemetrySample:
        ...

    def stream(self) -> AsyncIterator[TelemetrySample]:
        ...
