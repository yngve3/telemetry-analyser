"""Telemetry output encoder port."""

from typing import Any, Protocol

from telemetry_converter.domain.models import UnifiedTelemetryPayload


class TelemetryOutputEncoder(Protocol):
    """Adapter for encoding unified telemetry into the requested target."""

    def encode(self, telemetry: UnifiedTelemetryPayload) -> Any:
        ...
