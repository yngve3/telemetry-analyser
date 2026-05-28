"""Telemetry input decoder port."""

from typing import Protocol

from telemetry_converter.domain.models import UnifiedTelemetryPayload


class TelemetryInputDecoder(Protocol):
    """Adapter for decoding source payloads into unified telemetry."""

    def decode(self, payload: bytes) -> UnifiedTelemetryPayload:
        ...
