"""Rule contracts for telemetry anomaly detection."""

from datetime import datetime
from typing import Protocol

from analysis_module.domain.anomalies import DetectedAnomaly
from analysis_module.domain.models import UnifiedTelemetry


class TelemetryHistoryView(Protocol):
    """Read-only history contract used by domain rules."""

    def previous(self) -> UnifiedTelemetry | None:
        ...

    def recent(
        self,
        seconds: float,
        current_time: datetime | None = None,
    ) -> tuple[UnifiedTelemetry, ...]:
        ...

    def samples(self) -> tuple[UnifiedTelemetry, ...]:
        ...


class TelemetryRule(Protocol):
    """Contract implemented by deterministic telemetry rules."""

    @property
    def name(self) -> str:
        """Rule public name."""
        ...

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistoryView,
    ) -> DetectedAnomaly | None:
        """Evaluate one telemetry sample in the context of stored history."""
        ...
