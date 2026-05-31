"""Battery drop rule."""

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
class BatteryDropRule:
    """Detects abrupt battery percentage drops."""

    name: str = "BatteryDropRule"
    min_drop_percent: float = 5.0
    max_drop_percent_per_sec: float = 1.0

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        previous = history.previous()
        if previous is None:
            return None

        elapsed_sec = elapsed_seconds(previous, current)
        if elapsed_sec <= 0.0:
            return None

        drop_percent = previous.battery_percent - current.battery_percent
        if drop_percent < self.min_drop_percent:
            return None

        drop_percent_per_sec = drop_percent / elapsed_sec
        if drop_percent_per_sec <= self.max_drop_percent_per_sec:
            return None

        severity = Severity.CRITICAL if drop_percent >= 20.0 else Severity.WARNING
        confidence = min(
            1.0,
            0.5 + drop_percent_per_sec / (self.max_drop_percent_per_sec * 2.0),
        )
        return DetectedAnomaly(
            type=AnomalyType.BATTERY_DROP,
            severity=severity,
            message="Battery percentage dropped faster than expected.",
            confidence=confidence,
            detector_name=self.name,
            affected_fields=("battery_percent",),
            evidence={
                "drop_percent": drop_percent,
                "elapsed_sec": elapsed_sec,
                "drop_percent_per_sec": drop_percent_per_sec,
                "threshold_percent_per_sec": self.max_drop_percent_per_sec,
            },
        )
