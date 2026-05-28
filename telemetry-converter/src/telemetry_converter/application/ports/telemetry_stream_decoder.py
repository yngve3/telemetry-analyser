"""Telemetry stream decoder port."""

from typing import Protocol

from telemetry_converter.domain.models import UnifiedTelemetryPayload


class TelemetryStreamDecoder(Protocol):
    """Stateful decoder for fragmented or multi-rate telemetry streams."""

    def update(self, payload: bytes) -> UnifiedTelemetryPayload | None:
        ...
