"""Telemetry validation port."""

from typing import Protocol
from typing import Any

from telemetry_source_backend.domain.common.models import TelemetrySample


class TelemetryValidator(Protocol):
    """Port for validating telemetry before it leaves the backend."""

    def validate_sample(self, sample: TelemetrySample) -> None:
        ...

    def validate_payload(self, payload: dict[str, Any]) -> None:
        ...
