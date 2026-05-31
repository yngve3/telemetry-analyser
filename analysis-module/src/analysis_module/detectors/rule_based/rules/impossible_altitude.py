"""Impossible altitude rule."""

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
class ImpossibleAltitudeRule:
    """Detects altitude outside expected physical limits."""

    name: str = "ImpossibleAltitudeRule"
    min_altitude_m: float = -500.0
    max_altitude_m: float = 30_000.0

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        del history
        if self.min_altitude_m <= current.altitude_m <= self.max_altitude_m:
            return None

        return DetectedAnomaly(
            type=AnomalyType.IMPOSSIBLE_ALTITUDE,
            severity=Severity.CRITICAL,
            message=(
                "Altitude is outside the physically expected range: "
                f"{current.altitude_m:.1f} m."
            ),
            confidence=1.0,
            detector_name=self.name,
            affected_fields=("altitude_m",),
            evidence={
                "altitude_m": current.altitude_m,
                "min_altitude_m": self.min_altitude_m,
                "max_altitude_m": self.max_altitude_m,
            },
        )
