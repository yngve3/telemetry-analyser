"""Motion inconsistency rule."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    Severity,
    UnifiedTelemetry,
)
from analysis_module.features.feature_extractor import distance_meters, elapsed_seconds
from analysis_module.features.telemetry_history import TelemetryHistory


@dataclass(frozen=True, slots=True)
class MotionInconsistencyRule:
    """Detects inconsistent speed values across telemetry fields."""

    name: str = "MotionInconsistencyRule"
    max_speed_delta_m_s: float = 5.0
    min_reference_speed_m_s: float = 1.0

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        if current.ground_speed_m_s is None:
            return None

        vector_speed_m_s = _horizontal_vector_speed(current)
        if vector_speed_m_s is not None:
            return self._evaluate_speed_delta(
                reported_speed_m_s=current.ground_speed_m_s,
                reference_speed_m_s=vector_speed_m_s,
                source="velocity_vector",
            )

        previous = history.previous()
        if previous is None:
            return None
        elapsed_sec = elapsed_seconds(previous, current)
        if elapsed_sec <= 0.0:
            return None

        distance_delta_m = distance_meters(previous, current)
        implied_speed_m_s = distance_delta_m / elapsed_sec
        return self._evaluate_speed_delta(
            reported_speed_m_s=current.ground_speed_m_s,
            reference_speed_m_s=implied_speed_m_s,
            source="position_delta",
            extra_evidence={
                "distance_delta_m": distance_delta_m,
                "elapsed_sec": elapsed_sec,
            },
        )

    def _evaluate_speed_delta(
        self,
        reported_speed_m_s: float,
        reference_speed_m_s: float,
        source: str,
        extra_evidence: dict[str, float] | None = None,
    ) -> DetectedAnomaly | None:
        if reference_speed_m_s < self.min_reference_speed_m_s:
            return None

        speed_delta_m_s = abs(reference_speed_m_s - reported_speed_m_s)
        if speed_delta_m_s <= self.max_speed_delta_m_s:
            return None

        evidence = {
            "reported_speed_m_s": reported_speed_m_s,
            "reference_speed_m_s": reference_speed_m_s,
            "speed_delta_m_s": speed_delta_m_s,
            "max_speed_delta_m_s": self.max_speed_delta_m_s,
            "reference_source": source,
        }
        if extra_evidence is not None:
            evidence.update(extra_evidence)

        severity = (
            Severity.CRITICAL
            if speed_delta_m_s > self.max_speed_delta_m_s * 3.0
            else Severity.WARNING
        )
        return DetectedAnomaly(
            type=AnomalyType.MOTION_INCONSISTENCY,
            severity=severity,
            message="Telemetry motion fields report inconsistent speeds.",
            confidence=min(1.0, 0.5 + speed_delta_m_s / 20.0),
            detector_name=self.name,
            evidence=evidence,
        )


def _horizontal_vector_speed(current: UnifiedTelemetry) -> float | None:
    if current.velocity_x_m_s is None or current.velocity_y_m_s is None:
        return None
    return sqrt(current.velocity_x_m_s**2 + current.velocity_y_m_s**2)
