"""IMU spike rule."""

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
class ImuSpikeRule:
    """Detects sudden attitude or angular-rate spikes."""

    name: str = "ImuSpikeRule"
    max_angular_rate_rad_s: float = 6.0
    max_attitude_change_rad_s: float = 5.0

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        rates = [
            abs(value)
            for value in (
                current.roll_rate_rad_s,
                current.pitch_rate_rad_s,
                current.yaw_rate_rad_s,
            )
            if value is not None
        ]
        max_rate = max(rates, default=0.0)

        max_attitude_change_rate = 0.0
        previous = history.previous()
        if previous is not None:
            elapsed_sec = elapsed_seconds(previous, current)
            if elapsed_sec > 0.0:
                max_attitude_change_rate = max(
                    _change_rate(previous.roll_rad, current.roll_rad, elapsed_sec),
                    _change_rate(previous.pitch_rad, current.pitch_rad, elapsed_sec),
                    _change_rate(previous.yaw_rad, current.yaw_rad, elapsed_sec),
                )

        if (
            max_rate <= self.max_angular_rate_rad_s
            and max_attitude_change_rate <= self.max_attitude_change_rad_s
        ):
            return None

        return DetectedAnomaly(
            type=AnomalyType.IMU_SPIKE,
            severity=Severity.WARNING,
            message="IMU attitude or angular-rate data contains a sudden spike.",
            confidence=1.0,
            detector_name=self.name,
            affected_fields=(
                "roll_rad",
                "pitch_rad",
                "yaw_rad",
                "roll_rate_rad_s",
                "pitch_rate_rad_s",
                "yaw_rate_rad_s",
            ),
            evidence={
                "max_rate_rad_s": max_rate,
                "max_attitude_change_rad_s": max_attitude_change_rate,
                "rate_threshold_rad_s": self.max_angular_rate_rad_s,
                "attitude_change_threshold_rad_s": self.max_attitude_change_rad_s,
            },
        )


def _change_rate(
    previous: float | None,
    current: float | None,
    elapsed_sec: float,
) -> float:
    if previous is None or current is None:
        return 0.0
    return abs(current - previous) / elapsed_sec
