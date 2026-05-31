"""Correlation-based telemetry anomaly detector."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from analysis_module.application.context import AnalysisContext
from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    DetectorKind,
    DetectorOutput,
    Severity,
    UnifiedTelemetry,
)
from analysis_module.domain.anomalies import EvidenceValue
from analysis_module.features.feature_extractor import distance_meters, elapsed_seconds


@dataclass(frozen=True, slots=True)
class CorrelationBasedDetector:
    """Detects anomalies from cross-channel telemetry relationships."""

    name: str = "correlation_based"
    kind: DetectorKind = DetectorKind.MODEL_BASED
    model_name: str = "correlation_baseline_v1"
    max_ground_speed_delta_m_s: float = 8.0
    max_vertical_speed_delta_m_s: float = 3.0
    min_position_delta_m: float = 20.0
    min_battery_drop_percent: float = 5.0
    min_voltage_drop_v: float = 0.2

    def analyze(self, context: AnalysisContext) -> DetectorOutput:
        previous = context.history.previous()
        if previous is None:
            return self._empty_output()

        elapsed_sec = elapsed_seconds(previous, context.current)
        if elapsed_sec <= 0.0:
            return self._empty_output()

        anomalies = tuple(
            anomaly
            for anomaly in (
                self._motion_anomaly(previous, context.current, elapsed_sec),
                self._battery_anomaly(previous, context.current, elapsed_sec),
            )
            if anomaly is not None
        )
        return DetectorOutput(
            detector_name=self.name,
            detector_kind=self.kind,
            anomalies=anomalies,
        )

    def _motion_anomaly(
        self,
        previous: UnifiedTelemetry,
        current: UnifiedTelemetry,
        elapsed_sec: float,
    ) -> DetectedAnomaly | None:
        evidence: dict[str, EvidenceValue] = {"elapsed_sec": elapsed_sec}
        affected_parameters: list[str] = []
        max_ratio = 0.0

        distance_delta_m = distance_meters(previous, current)
        implied_speed_m_s = distance_delta_m / elapsed_sec
        reported_speed_m_s = current.ground_speed_m_s
        if (
            reported_speed_m_s is not None
            and distance_delta_m >= self.min_position_delta_m
        ):
            speed_delta_m_s = abs(implied_speed_m_s - reported_speed_m_s)
            evidence.update(
                {
                    "distance_delta_m": distance_delta_m,
                    "implied_speed_m_s": implied_speed_m_s,
                    "reported_speed_m_s": reported_speed_m_s,
                    "ground_speed_delta_m_s": speed_delta_m_s,
                    "max_ground_speed_delta_m_s": self.max_ground_speed_delta_m_s,
                }
            )
            if speed_delta_m_s > self.max_ground_speed_delta_m_s:
                affected_parameters.extend(
                    ("latitude_deg", "longitude_deg", "ground_speed_m_s")
                )
                max_ratio = max(
                    max_ratio,
                    speed_delta_m_s / self.max_ground_speed_delta_m_s,
                )

        vertical_speed_m_s = current.vertical_speed_m_s
        if vertical_speed_m_s is not None:
            altitude_delta_m = current.altitude_m - previous.altitude_m
            implied_vertical_speed_m_s = altitude_delta_m / elapsed_sec
            vertical_delta_m_s = abs(implied_vertical_speed_m_s - vertical_speed_m_s)
            evidence.update(
                {
                    "altitude_delta_m": altitude_delta_m,
                    "implied_vertical_speed_m_s": implied_vertical_speed_m_s,
                    "reported_vertical_speed_m_s": vertical_speed_m_s,
                    "vertical_speed_delta_m_s": vertical_delta_m_s,
                    "max_vertical_speed_delta_m_s": self.max_vertical_speed_delta_m_s,
                }
            )
            if vertical_delta_m_s > self.max_vertical_speed_delta_m_s:
                affected_parameters.extend(("altitude_m", "vertical_speed_m_s"))
                max_ratio = max(
                    max_ratio,
                    vertical_delta_m_s / self.max_vertical_speed_delta_m_s,
                )

        vector_speed_m_s = _horizontal_vector_speed(current)
        if vector_speed_m_s is not None and reported_speed_m_s is not None:
            vector_delta_m_s = abs(vector_speed_m_s - reported_speed_m_s)
            evidence.update(
                {
                    "vector_speed_m_s": vector_speed_m_s,
                    "vector_speed_delta_m_s": vector_delta_m_s,
                }
            )
            if vector_delta_m_s > self.max_ground_speed_delta_m_s:
                affected_parameters.extend(
                    ("velocity_x_m_s", "velocity_y_m_s", "ground_speed_m_s")
                )
                max_ratio = max(
                    max_ratio,
                    vector_delta_m_s / self.max_ground_speed_delta_m_s,
                )

        if max_ratio <= 1.0:
            return None

        return DetectedAnomaly(
            type=AnomalyType.MOTION_INCONSISTENCY,
            severity=Severity.CRITICAL if max_ratio >= 3.0 else Severity.WARNING,
            message="Telemetry channels describe inconsistent motion.",
            confidence=min(1.0, 0.5 + max_ratio / 6.0),
            source=self.kind.value,
            detector_kind=self.kind.value,
            detector_name=self.name,
            model_name=self.model_name,
            affected_parameters=tuple(dict.fromkeys(affected_parameters)),
            evidence=evidence,
            window_start=previous.timestamp,
            window_end=current.timestamp,
            probable_cause=(
                "Position, speed, or velocity channels are no longer mutually "
                "consistent."
            ),
        )

    def _battery_anomaly(
        self,
        previous: UnifiedTelemetry,
        current: UnifiedTelemetry,
        elapsed_sec: float,
    ) -> DetectedAnomaly | None:
        if previous.battery_voltage_v is None or current.battery_voltage_v is None:
            return None

        battery_drop_percent = previous.battery_percent - current.battery_percent
        voltage_drop_v = previous.battery_voltage_v - current.battery_voltage_v
        if battery_drop_percent < self.min_battery_drop_percent:
            return None
        if voltage_drop_v >= self.min_voltage_drop_v:
            return None

        ratio = battery_drop_percent / self.min_battery_drop_percent
        return DetectedAnomaly(
            type=AnomalyType.BATTERY_DROP,
            severity=Severity.CRITICAL if ratio >= 4.0 else Severity.WARNING,
            message="Battery percentage dropped without a matching voltage drop.",
            confidence=min(1.0, 0.5 + ratio / 8.0),
            source=self.kind.value,
            detector_kind=self.kind.value,
            detector_name=self.name,
            model_name=self.model_name,
            affected_parameters=("battery_percent", "battery_voltage_v"),
            evidence={
                "battery_drop_percent": battery_drop_percent,
                "voltage_drop_v": voltage_drop_v,
                "elapsed_sec": elapsed_sec,
                "min_battery_drop_percent": self.min_battery_drop_percent,
                "min_voltage_drop_v": self.min_voltage_drop_v,
            },
            window_start=previous.timestamp,
            window_end=current.timestamp,
            probable_cause=(
                "Battery percentage and voltage telemetry changed inconsistently."
            ),
        )

    def _empty_output(self) -> DetectorOutput:
        return DetectorOutput(detector_name=self.name, detector_kind=self.kind)


def _horizontal_vector_speed(current: UnifiedTelemetry) -> float | None:
    if current.velocity_x_m_s is None or current.velocity_y_m_s is None:
        return None
    return sqrt(current.velocity_x_m_s**2 + current.velocity_y_m_s**2)
