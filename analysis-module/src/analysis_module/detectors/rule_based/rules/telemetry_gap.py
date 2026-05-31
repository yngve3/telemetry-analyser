"""Telemetry stream gap rule."""

from __future__ import annotations

from dataclasses import dataclass

from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    Severity,
    UnifiedTelemetry,
)
from analysis_module.features.feature_extractor import elapsed_seconds
from analysis_module.features.telemetry_history import TelemetryHistory


@dataclass(frozen=True, slots=True)
class TelemetryGapRule:
    """Detects unexpectedly large time gaps between telemetry samples."""

    name: str = "TelemetryGapRule"
    max_elapsed_sec: float = 10.0

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        previous = history.previous()
        if previous is None:
            return None

        elapsed_sec = elapsed_seconds(previous, current)
        if elapsed_sec <= self.max_elapsed_sec:
            return None

        severity = (
            Severity.CRITICAL
            if elapsed_sec > self.max_elapsed_sec * 3.0
            else Severity.WARNING
        )
        return DetectedAnomaly(
            type=AnomalyType.TELEMETRY_GAP,
            severity=severity,
            message="Telemetry stream has a larger than expected time gap.",
            confidence=1.0,
            detector_name=self.name,
            affected_fields=("timestamp",),
            evidence={
                "previous_timestamp": previous.timestamp.isoformat(),
                "current_timestamp": current.timestamp.isoformat(),
                "gap_ms": int(elapsed_sec * 1000),
                "threshold_ms": int(self.max_elapsed_sec * 1000),
            },
        )
