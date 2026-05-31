"""GPS spoofing rule."""

from __future__ import annotations

from dataclasses import dataclass

from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    Severity,
    UnifiedTelemetry,
)
from analysis_module.features.feature_extractor import distance_meters, elapsed_seconds
from analysis_module.features.telemetry_history import TelemetryHistory


@dataclass(frozen=True, slots=True)
class GpsSpoofingRule:
    """Detects location jumps inconsistent with reported speed."""

    name: str = "GpsSpoofingRule"
    max_implied_speed_m_s: float = 70.0
    speed_margin_m_s: float = 15.0
    min_distance_delta_m: float = 50.0

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        previous = _previous_with_elapsed(history, current)
        if previous is None:
            return None

        elapsed_sec = elapsed_seconds(previous, current)
        distance_delta_m = distance_meters(previous, current)
        if distance_delta_m < self.min_distance_delta_m:
            return None

        implied_speed_m_s = distance_delta_m / elapsed_sec
        reported_speed_m_s = current.ground_speed_m_s or 0.0
        allowed_speed_m_s = max(
            self.max_implied_speed_m_s,
            reported_speed_m_s + self.speed_margin_m_s,
        )

        if implied_speed_m_s <= allowed_speed_m_s:
            return None

        severity = (
            Severity.CRITICAL
            if implied_speed_m_s > allowed_speed_m_s * 2.0
            else Severity.WARNING
        )
        confidence = min(1.0, 0.5 + (implied_speed_m_s - allowed_speed_m_s) / allowed_speed_m_s)
        return DetectedAnomaly(
            type=AnomalyType.GPS_SPOOFING,
            severity=severity,
            message="GPS position changed faster than the reported motion allows.",
            confidence=confidence,
            detector_name=self.name,
            affected_fields=("latitude_deg", "longitude_deg", "ground_speed_m_s"),
            evidence={
                "distance_delta_m": distance_delta_m,
                "time_delta_s": elapsed_sec,
                "calculated_speed_m_s": implied_speed_m_s,
                "reported_speed_m_s": reported_speed_m_s,
                "threshold_m_s": allowed_speed_m_s,
            },
        )


def _previous_with_elapsed(
    history: TelemetryHistory,
    current: UnifiedTelemetry,
) -> UnifiedTelemetry | None:
    for previous in reversed(history.samples()):
        if elapsed_seconds(previous, current) > 0.0:
            return previous
    return None
