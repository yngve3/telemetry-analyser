"""GPS signal loss rule."""

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
class GpsSignalLossRule:
    """Detects missing GPS satellites or unusable GPS fix."""

    name: str = "GpsSignalLossRule"
    min_satellites: int = 1
    min_fix_type: int = 2

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        del history
        satellites = (
            current.satellites_visible
            if current.satellites_visible is not None
            else current.satellites
        )
        fix_type = current.gps_fix_type
        has_satellite_loss = satellites < self.min_satellites
        has_bad_fix = fix_type is not None and fix_type < self.min_fix_type

        if not has_satellite_loss and not has_bad_fix:
            return None

        severity = Severity.CRITICAL if has_satellite_loss else Severity.WARNING
        return DetectedAnomaly(
            type=AnomalyType.GPS_SIGNAL_LOSS,
            severity=severity,
            message="GPS signal is unavailable or below the required fix quality.",
            confidence=1.0 if has_satellite_loss else 0.8,
            detector_name=self.name,
            affected_fields=("satellites", "satellites_visible", "gps_fix_type"),
            evidence={
                "satellites_visible": satellites,
                "gps_fix_type": fix_type,
                "min_satellites": self.min_satellites,
                "min_fix_type": self.min_fix_type,
            },
        )
