"""Telemetry freeze rule."""

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
class TelemetryFreezeRule:
    """Detects unchanged telemetry values over a suspicious interval."""

    name: str = "TelemetryFreezeRule"
    min_elapsed_sec: float = 5.0
    position_epsilon_m: float = 0.1
    value_epsilon: float = 0.001

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        previous = history.previous()
        if previous is None:
            return None

        elapsed_sec = elapsed_seconds(previous, current)
        if elapsed_sec < self.min_elapsed_sec:
            return None

        distance_delta_m = distance_meters(previous, current)
        if distance_delta_m > self.position_epsilon_m:
            return None

        unchanged = all(
            _is_close(previous_value, current_value, self.value_epsilon)
            for previous_value, current_value in (
                (previous.altitude_m, current.altitude_m),
                (previous.battery_percent, current.battery_percent),
                (previous.ground_speed_m_s, current.ground_speed_m_s),
                (previous.vertical_speed_m_s, current.vertical_speed_m_s),
                (previous.heading_deg, current.heading_deg),
                (previous.roll_rad, current.roll_rad),
                (previous.pitch_rad, current.pitch_rad),
                (previous.yaw_rad, current.yaw_rad),
            )
        )
        if not unchanged:
            return None

        return DetectedAnomaly(
            type=AnomalyType.TELEMETRY_FREEZE,
            severity=Severity.WARNING,
            message="Telemetry values did not change over the configured interval.",
            confidence=0.9,
            detector_name=self.name,
            evidence={
                "elapsed_sec": elapsed_sec,
                "distance_delta_m": distance_delta_m,
                "min_elapsed_sec": self.min_elapsed_sec,
            },
        )


def _is_close(
    previous: float | int | None,
    current: float | int | None,
    epsilon: float,
) -> bool:
    if previous is None and current is None:
        return True
    if previous is None or current is None:
        return False
    return abs(float(current) - float(previous)) <= epsilon
