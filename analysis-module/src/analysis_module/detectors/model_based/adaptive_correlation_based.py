"""Adaptive correlation-based telemetry anomaly detector."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import atan2, cos, degrees, radians, sin
from typing import Any

from analysis_module.application.context import AnalysisContext
from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    DetectorKind,
    DetectorOutput,
    DetectorStatus,
    Severity,
    UnifiedTelemetry,
)
from analysis_module.features.feature_extractor import distance_meters, elapsed_seconds

POSITION_SPEED_ERROR = "position_speed_error"
ALTITUDE_VELOCITY_ERROR = "altitude_velocity_error"
HEADING_YAW_ERROR = "heading_yaw_error"
ERROR_NAMES = (
    POSITION_SPEED_ERROR,
    ALTITUDE_VELOCITY_ERROR,
    HEADING_YAW_ERROR,
)


@dataclass(frozen=True, slots=True)
class ConsistencyErrorSnapshot:
    """Consistency errors calculated for one telemetry transition."""

    elapsed_sec: float
    distance_delta_m: float
    errors: dict[str, float]
    evidence: dict[str, Any]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


@dataclass(slots=True)
class AdaptiveCorrelationProfile:
    """Sliding-window profile of normal consistency errors."""

    max_size: int = 1_000
    min_samples: int = 100
    percentile: float = 0.99
    threshold_multiplier: float = 1.2
    _values: dict[str, deque[float]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_size <= 0:
            raise ValueError("Adaptive profile max_size must be positive.")
        if self.min_samples <= 0:
            raise ValueError("Adaptive profile min_samples must be positive.")
        if not 0.0 < self.percentile <= 1.0:
            raise ValueError("Adaptive profile percentile must be in (0, 1].")
        if self.threshold_multiplier <= 0.0:
            raise ValueError("Adaptive profile threshold_multiplier must be positive.")
        self._values = {
            name: deque(maxlen=self.max_size)
            for name in ERROR_NAMES
        }

    def update(self, snapshot: ConsistencyErrorSnapshot) -> None:
        for name, value in snapshot.errors.items():
            if name in self._values:
                self._values[name].append(value)

    def count(self, name: str) -> int:
        return len(self._values.get(name, ()))

    def counts(self) -> dict[str, int]:
        return {name: len(values) for name, values in self._values.items()}

    def ready_for(self, name: str) -> bool:
        return self.count(name) >= self.min_samples

    @property
    def has_ready_thresholds(self) -> bool:
        return any(self.ready_for(name) for name in ERROR_NAMES)

    def adaptive_threshold(self, name: str) -> float | None:
        values = self._values.get(name)
        if values is None or len(values) < self.min_samples:
            return None
        return _percentile(tuple(values), self.percentile) * self.threshold_multiplier

    def threshold(self, name: str, static_threshold: float) -> tuple[float, str]:
        adaptive_threshold = self.adaptive_threshold(name)
        if adaptive_threshold is None:
            return static_threshold, "static"
        if adaptive_threshold <= static_threshold:
            return static_threshold, "static"
        return adaptive_threshold, "adaptive"

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_size": self.max_size,
            "min_samples": self.min_samples,
            "percentile": self.percentile,
            "threshold_multiplier": self.threshold_multiplier,
            "counts": self.counts(),
            "adaptive_thresholds": {
                name: self.adaptive_threshold(name)
                for name in ERROR_NAMES
            },
            "errors": {
                name: list(values)
                for name, values in self._values.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AdaptiveCorrelationProfile":
        profile = cls(
            max_size=int(payload.get("max_size", 1_000)),
            min_samples=int(payload.get("min_samples", 100)),
            percentile=float(payload.get("percentile", 0.99)),
            threshold_multiplier=float(payload.get("threshold_multiplier", 1.2)),
        )
        errors = payload.get("errors", {})
        if isinstance(errors, dict):
            for name in ERROR_NAMES:
                values = errors.get(name, ())
                if isinstance(values, list):
                    for value in values[-profile.max_size :]:
                        if isinstance(value, int | float) and not isinstance(value, bool):
                            profile._values[name].append(float(value))
        return profile


@dataclass(slots=True)
class AdaptiveCorrelationBasedDetector:
    """Detects parameter inconsistency with a gated adaptive normal profile."""

    name: str = "adaptive_correlation_based"
    kind: DetectorKind = DetectorKind.MODEL_BASED
    model_name: str = "adaptive_correlation_profile_v1"
    max_ground_speed_delta_m_s: float = 8.0
    max_vertical_speed_delta_m_s: float = 3.0
    max_heading_yaw_delta_deg: float = 45.0
    min_heading_distance_m: float = 0.5
    min_message_quality: float = 0.7
    profile: AdaptiveCorrelationProfile = field(
        default_factory=AdaptiveCorrelationProfile
    )
    _pending_profile_update: ConsistencyErrorSnapshot | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def analyze(self, context: AnalysisContext) -> DetectorOutput:
        self._pending_profile_update = None
        previous = context.history.previous()
        if previous is None:
            return self._empty_output()

        elapsed_sec = elapsed_seconds(previous, context.current)
        if elapsed_sec <= 0.0:
            return self._empty_output()

        if not self._fresh_enough(context.current):
            return DetectorOutput(
                detector_name=self.name,
                detector_kind=self.kind,
                status=DetectorStatus.NOT_READY,
                message="Telemetry freshness is below the adaptive correlation threshold.",
            )

        snapshot = _calculate_errors(
            previous=previous,
            current=context.current,
            elapsed_sec=elapsed_sec,
            min_heading_distance_m=self.min_heading_distance_m,
        )
        if not snapshot.has_errors:
            return self._empty_output()

        self._pending_profile_update = snapshot
        anomaly = self._detect_anomaly(previous, context.current, snapshot)
        if anomaly is None:
            return DetectorOutput(
                detector_name=self.name,
                detector_kind=self.kind,
                message=self._profile_message(),
            )

        return DetectorOutput(
            detector_name=self.name,
            detector_kind=self.kind,
            anomalies=(anomaly,),
            message=self._profile_message(),
        )

    def commit_profile_update(self) -> None:
        if self._pending_profile_update is not None:
            self.profile.update(self._pending_profile_update)
        self._pending_profile_update = None

    def discard_profile_update(self) -> None:
        self._pending_profile_update = None

    def _detect_anomaly(
        self,
        previous: UnifiedTelemetry,
        current: UnifiedTelemetry,
        snapshot: ConsistencyErrorSnapshot,
    ) -> DetectedAnomaly | None:
        thresholds: dict[str, float] = {}
        threshold_sources: dict[str, str] = {}
        exceeded: dict[str, float] = {}
        affected_parameters: list[str] = []
        max_ratio = 0.0

        for name, error_value in snapshot.errors.items():
            threshold, source = self.profile.threshold(
                name,
                self._static_threshold(name),
            )
            thresholds[name] = threshold
            threshold_sources[name] = source
            if error_value > threshold:
                exceeded[name] = error_value
                max_ratio = max(max_ratio, error_value / threshold)
                affected_parameters.extend(_affected_parameters(name))

        if not exceeded:
            return None

        evidence = {
            **snapshot.evidence,
            "errors": snapshot.errors,
            "thresholds": thresholds,
            "threshold_sources": threshold_sources,
            "exceeded_errors": exceeded,
            "profile_counts": self.profile.counts(),
            "profile_has_ready_thresholds": self.profile.has_ready_thresholds,
            "mode": (
                "detection"
                if self.profile.has_ready_thresholds
                else "calibration"
            ),
        }
        return DetectedAnomaly(
            type=AnomalyType.MOTION_INCONSISTENCY,
            severity=Severity.CRITICAL if max_ratio >= 2.0 else Severity.WARNING,
            message="Telemetry parameters violate the adaptive consistency profile.",
            confidence=min(1.0, 0.5 + (max_ratio - 1.0) / 2.0),
            source=self.kind.value,
            detector_kind=self.kind.value,
            detector_name=self.name,
            model_name=self.model_name,
            score=max_ratio,
            affected_parameters=tuple(dict.fromkeys(affected_parameters)),
            evidence=evidence,
            window_start=previous.timestamp,
            window_end=current.timestamp,
            probable_cause=(
                "Position, speed, altitude, or attitude channels are no longer "
                "consistent with the learned normal profile."
            ),
        )

    def _static_threshold(self, name: str) -> float:
        if name == POSITION_SPEED_ERROR:
            return self.max_ground_speed_delta_m_s
        if name == ALTITUDE_VELOCITY_ERROR:
            return self.max_vertical_speed_delta_m_s
        if name == HEADING_YAW_ERROR:
            return self.max_heading_yaw_delta_deg
        raise ValueError(f"Unknown adaptive correlation error: {name}")

    def _profile_message(self) -> str | None:
        if self.profile.has_ready_thresholds:
            return None
        return "Adaptive correlation profile is collecting normal telemetry."

    def _fresh_enough(self, telemetry: UnifiedTelemetry) -> bool:
        if telemetry.message_quality is None:
            return True
        return telemetry.message_quality >= self.min_message_quality

    def _empty_output(self) -> DetectorOutput:
        return DetectorOutput(detector_name=self.name, detector_kind=self.kind)


def _calculate_errors(
    previous: UnifiedTelemetry,
    current: UnifiedTelemetry,
    elapsed_sec: float,
    min_heading_distance_m: float,
) -> ConsistencyErrorSnapshot:
    distance_delta_m = distance_meters(previous, current)
    errors: dict[str, float] = {}
    evidence: dict[str, Any] = {
        "elapsed_sec": elapsed_sec,
        "distance_delta_m": distance_delta_m,
    }

    if current.ground_speed_m_s is not None:
        implied_speed_m_s = distance_delta_m / elapsed_sec
        position_speed_error = abs(implied_speed_m_s - current.ground_speed_m_s)
        errors[POSITION_SPEED_ERROR] = position_speed_error
        evidence.update(
            {
                "implied_speed_m_s": implied_speed_m_s,
                "reported_speed_m_s": current.ground_speed_m_s,
            }
        )

    if current.vertical_speed_m_s is not None:
        altitude_delta_m = current.altitude_m - previous.altitude_m
        implied_vertical_speed_m_s = altitude_delta_m / elapsed_sec
        altitude_velocity_error = abs(
            implied_vertical_speed_m_s - current.vertical_speed_m_s
        )
        errors[ALTITUDE_VELOCITY_ERROR] = altitude_velocity_error
        evidence.update(
            {
                "altitude_delta_m": altitude_delta_m,
                "implied_vertical_speed_m_s": implied_vertical_speed_m_s,
                "reported_vertical_speed_m_s": current.vertical_speed_m_s,
            }
        )

    if current.yaw_rad is not None and distance_delta_m >= min_heading_distance_m:
        movement_heading_deg = _bearing_degrees(previous, current)
        yaw_deg = degrees(current.yaw_rad) % 360.0
        heading_yaw_error = _angle_delta_degrees(movement_heading_deg, yaw_deg)
        errors[HEADING_YAW_ERROR] = heading_yaw_error
        evidence.update(
            {
                "movement_heading_deg": movement_heading_deg,
                "yaw_deg": yaw_deg,
            }
        )

    return ConsistencyErrorSnapshot(
        elapsed_sec=elapsed_sec,
        distance_delta_m=distance_delta_m,
        errors=errors,
        evidence=evidence,
    )


def _affected_parameters(error_name: str) -> tuple[str, ...]:
    if error_name == POSITION_SPEED_ERROR:
        return ("latitude_deg", "longitude_deg", "ground_speed_m_s")
    if error_name == ALTITUDE_VELOCITY_ERROR:
        return ("altitude_m", "vertical_speed_m_s")
    if error_name == HEADING_YAW_ERROR:
        return ("latitude_deg", "longitude_deg", "yaw_rad")
    return ()


def _bearing_degrees(
    previous: UnifiedTelemetry,
    current: UnifiedTelemetry,
) -> float:
    previous_lat = radians(previous.latitude_deg)
    current_lat = radians(current.latitude_deg)
    delta_lon = radians(current.longitude_deg - previous.longitude_deg)
    y = sin(delta_lon) * cos(current_lat)
    x = (
        cos(previous_lat) * sin(current_lat)
        - sin(previous_lat) * cos(current_lat) * cos(delta_lon)
    )
    return (degrees(atan2(y, x)) + 360.0) % 360.0


def _angle_delta_degrees(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def _percentile(values: tuple[float, ...], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    rank = (len(ordered) - 1) * percentile
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = rank - lower_index
    return ordered[lower_index] + (
        ordered[upper_index] - ordered[lower_index]
    ) * fraction
