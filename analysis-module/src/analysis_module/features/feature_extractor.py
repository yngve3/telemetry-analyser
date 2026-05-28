"""Feature extraction for telemetry samples."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from analysis_module.domain.models import UnifiedTelemetry
from analysis_module.features.feature_vector import FeatureVector
from analysis_module.features.feature_window import FeatureWindow


@dataclass(frozen=True, slots=True)
class TelemetryFeatureExtractor:
    """Extracts stable ordered features for rules and future models."""

    feature_names: tuple[str, ...] = (
        "battery_percent",
        "battery_voltage_v",
        "satellites_visible",
        "gps_fix_type",
        "gps_eph",
        "gps_epv",
        "altitude_m",
        "ground_speed_m_s",
        "vertical_speed_m_s",
        "roll_rad",
        "pitch_rad",
        "yaw_rad",
        "roll_rate_rad_s",
        "pitch_rate_rad_s",
        "yaw_rate_rad_s",
        "delta_position_m",
        "delta_altitude_m",
        "delta_battery_percent",
        "delta_heading_deg",
        "elapsed_sec",
    )

    def extract(
        self,
        current: UnifiedTelemetry,
        previous: UnifiedTelemetry | None = None,
    ) -> FeatureVector:
        elapsed_sec = _elapsed_seconds(previous, current)
        values = (
            current.battery_percent,
            _number(current.battery_voltage_v),
            float(_satellites(current)),
            _number(current.gps_fix_type),
            _number(current.gps_eph),
            _number(current.gps_epv),
            current.altitude_m,
            _number(current.ground_speed_m_s),
            _number(current.vertical_speed_m_s),
            _number(current.roll_rad),
            _number(current.pitch_rad),
            _number(current.yaw_rad),
            _number(current.roll_rate_rad_s),
            _number(current.pitch_rate_rad_s),
            _number(current.yaw_rate_rad_s),
            _distance_m(previous, current) if previous is not None else 0.0,
            current.altitude_m - previous.altitude_m if previous is not None else 0.0,
            (
                current.battery_percent - previous.battery_percent
                if previous is not None
                else 0.0
            ),
            _heading_delta_deg(previous, current) if previous is not None else 0.0,
            elapsed_sec,
        )
        return FeatureVector(self.feature_names, values)

    def extract_window(
        self,
        samples: Sequence[UnifiedTelemetry],
    ) -> FeatureWindow:
        vectors: list[FeatureVector] = []
        previous: UnifiedTelemetry | None = None
        for sample in samples:
            vectors.append(self.extract(sample, previous))
            previous = sample
        return FeatureWindow(
            feature_names=self.feature_names,
            vectors=tuple(vectors),
        )


def distance_meters(
    previous: UnifiedTelemetry,
    current: UnifiedTelemetry,
) -> float:
    return _distance_m(previous, current)


def elapsed_seconds(
    previous: UnifiedTelemetry | None,
    current: UnifiedTelemetry,
) -> float:
    return _elapsed_seconds(previous, current)


def heading_delta_degrees(
    previous: UnifiedTelemetry,
    current: UnifiedTelemetry,
) -> float:
    return _heading_delta_deg(previous, current)


def _number(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _satellites(telemetry: UnifiedTelemetry) -> int:
    if telemetry.satellites_visible is not None:
        return telemetry.satellites_visible
    return telemetry.satellites


def _elapsed_seconds(
    previous: UnifiedTelemetry | None,
    current: UnifiedTelemetry,
) -> float:
    if previous is None:
        return 0.0
    return max(0.0, (current.timestamp - previous.timestamp).total_seconds())


def _distance_m(
    previous: UnifiedTelemetry,
    current: UnifiedTelemetry,
) -> float:
    earth_radius_m = 6_371_000.0
    previous_lat = radians(previous.latitude_deg)
    current_lat = radians(current.latitude_deg)
    delta_lat = radians(current.latitude_deg - previous.latitude_deg)
    delta_lon = radians(current.longitude_deg - previous.longitude_deg)

    haversine = (
        sin(delta_lat / 2.0) ** 2
        + cos(previous_lat) * cos(current_lat) * sin(delta_lon / 2.0) ** 2
    )
    return 2.0 * earth_radius_m * asin(sqrt(haversine))


def _heading_delta_deg(
    previous: UnifiedTelemetry,
    current: UnifiedTelemetry,
) -> float:
    if previous.heading_deg is None or current.heading_deg is None:
        return 0.0
    delta = (current.heading_deg - previous.heading_deg + 180.0) % 360.0 - 180.0
    return abs(delta)
