"""Low battery rule."""

from __future__ import annotations

from dataclasses import dataclass

from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    Severity,
    UnifiedTelemetry,
)
from analysis_module.features.telemetry_history import TelemetryHistory


@dataclass(frozen=True, slots=True)
class LowBatteryRule:
    """Detects low remaining battery percentage."""

    name: str = "LowBatteryRule"
    warning_threshold_percent: float = 25.0
    critical_threshold_percent: float = 15.0

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        del history
        if current.battery_percent > self.warning_threshold_percent:
            return None

        severity = (
            Severity.CRITICAL
            if current.battery_percent <= self.critical_threshold_percent
            else Severity.WARNING
        )
        threshold = (
            self.critical_threshold_percent
            if severity == Severity.CRITICAL
            else self.warning_threshold_percent
        )
        confidence = min(1.0, max(0.5, 1.0 - current.battery_percent / threshold))
        return DetectedAnomaly(
            type=AnomalyType.LOW_BATTERY,
            severity=severity,
            message=f"Battery level is low: {current.battery_percent:.1f}%.",
            confidence=confidence,
            detector_name=self.name,
            evidence={
                "battery_percent": current.battery_percent,
                "warning_threshold_percent": self.warning_threshold_percent,
                "critical_threshold_percent": self.critical_threshold_percent,
            },
        )
