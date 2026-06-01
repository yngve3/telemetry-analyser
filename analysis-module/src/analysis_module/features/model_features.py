"""Runtime features that match trained model metadata contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import degrees, sqrt

from analysis_module.domain import UnifiedTelemetry
from analysis_module.features.feature_extractor import (
    distance_meters,
    elapsed_seconds,
)


SEQUENCE_FEATURE_NAMES: tuple[str, ...] = (
    "altitude",
    "vx",
    "vy",
    "vz",
    "ground_speed",
    "roll",
    "pitch",
    "yaw",
    "battery_voltage",
    "battery_remaining",
    "gps_fix_status",
    "satellites_visible",
    "eph",
    "epv",
    "position_speed_error",
    "altitude_velocity_error",
    "heading_yaw_error",
    "pos_test_ratio",
    "vel_test_ratio",
    "hgt_test_ratio",
    "mag_test_ratio",
    "hdg_test_ratio",
    "filter_fault_flags",
    "innovation_check_flags",
    "gps_check_fail_flags",
    "attitude_invalid",
    "angular_velocity_invalid",
    "local_position_invalid",
    "global_position_invalid",
    "local_velocity_invalid",
    "battery_warning",
    "fd_motor_failure",
    "fd_critical_failure",
    "fd_roll",
    "fd_pitch",
    "fd_alt",
    "fd_motor",
    "fd_battery",
    "fd_imbalanced_prop",
)

WINDOW_FEATURE_NAMES: tuple[str, ...] = (
    "position_speed_error_mean",
    "position_speed_error_max",
    "altitude_velocity_error_mean",
    "altitude_velocity_error_max",
    "heading_yaw_error_mean",
    "heading_yaw_error_max",
    "ground_speed_mean",
    "ground_speed_std",
    "vertical_speed_mean",
    "vertical_speed_std",
    "altitude_delta",
    "roll_mean",
    "roll_std",
    "pitch_mean",
    "pitch_std",
    "yaw_mean",
    "yaw_std",
    "yaw_delta",
    "battery_voltage_mean",
    "battery_remaining_mean",
    "gps_fix_status_mean",
    "satellites_visible_mean",
    "eph_mean",
    "epv_mean",
    "pos_test_ratio_mean",
    "pos_test_ratio_max",
    "vel_test_ratio_mean",
    "vel_test_ratio_max",
    "hgt_test_ratio_mean",
    "hgt_test_ratio_max",
    "mag_test_ratio_mean",
    "mag_test_ratio_max",
    "hdg_test_ratio_mean",
    "hdg_test_ratio_max",
    "filter_fault_flags_max",
    "innovation_check_flags_max",
    "gps_check_fail_flags_max",
    "attitude_invalid_max",
    "angular_velocity_invalid_max",
    "local_position_invalid_max",
    "global_position_invalid_max",
    "local_velocity_invalid_max",
    "battery_warning_max",
    "fd_motor_failure_max",
    "fd_critical_failure_max",
    "fd_roll_max",
    "fd_pitch_max",
    "fd_alt_max",
    "fd_motor_max",
    "fd_battery_max",
    "fd_imbalanced_prop_max",
)

_WINDOW_BASE_FEATURES: Mapping[str, str] = {
    "vertical_speed_mean": "vz",
    "vertical_speed_std": "vz",
}

_DIAGNOSTIC_MAX_FEATURES = {
    "filter_fault_flags",
    "innovation_check_flags",
    "gps_check_fail_flags",
    "attitude_invalid",
    "angular_velocity_invalid",
    "local_position_invalid",
    "global_position_invalid",
    "local_velocity_invalid",
    "battery_warning",
    "fd_motor_failure",
    "fd_critical_failure",
    "fd_roll",
    "fd_pitch",
    "fd_alt",
    "fd_motor",
    "fd_battery",
    "fd_imbalanced_prop",
}


def extract_window_feature_values(
    samples: Sequence[UnifiedTelemetry],
    feature_names: Sequence[str],
) -> dict[str, float]:
    rows = extract_sequence_feature_rows(samples, SEQUENCE_FEATURE_NAMES)
    values = _all_window_feature_values(samples, rows)
    return {name: float(values.get(name, 0.0)) for name in feature_names}


def extract_sequence_feature_values(
    samples: Sequence[UnifiedTelemetry],
    feature_names: Sequence[str],
) -> tuple[float, ...]:
    rows = extract_sequence_feature_rows(samples, feature_names)
    return tuple(
        row.get(feature_name, 0.0)
        for row in rows
        for feature_name in feature_names
    )


def extract_sequence_diagnostic_values(
    samples: Sequence[UnifiedTelemetry],
    feature_names: Sequence[str],
) -> dict[str, float]:
    rows = extract_sequence_feature_rows(samples, feature_names)
    result: dict[str, float] = {}
    for feature_name in feature_names:
        values = [row.get(feature_name, 0.0) for row in rows]
        if feature_name in _DIAGNOSTIC_MAX_FEATURES:
            result[feature_name] = _max(values)
        else:
            result[feature_name] = _mean(values)
    return result


def extract_sequence_feature_rows(
    samples: Sequence[UnifiedTelemetry],
    feature_names: Sequence[str],
) -> tuple[dict[str, float], ...]:
    rows: list[dict[str, float]] = []
    for index, sample in enumerate(samples):
        previous = samples[index - 1] if index > 0 else None
        row = _sequence_row(sample, previous)
        rows.append({name: float(row.get(name, 0.0)) for name in feature_names})
    return tuple(rows)


def _all_window_feature_values(
    samples: Sequence[UnifiedTelemetry],
    rows: Sequence[Mapping[str, float]],
) -> dict[str, float]:
    values: dict[str, float] = {
        "altitude_delta": _delta([sample.altitude_m for sample in samples]),
        "yaw_delta": _angle_delta(_row_values(rows, "yaw")),
    }

    for feature_name in WINDOW_FEATURE_NAMES:
        if feature_name in values:
            continue
        if feature_name.endswith("_mean"):
            base_name = _window_base_feature(feature_name, "_mean")
            values[feature_name] = _mean(_row_values(rows, base_name))
        elif feature_name.endswith("_max"):
            base_name = _window_base_feature(feature_name, "_max")
            values[feature_name] = _max(_row_values(rows, base_name))
        elif feature_name.endswith("_std"):
            base_name = _window_base_feature(feature_name, "_std")
            values[feature_name] = _stddev(_row_values(rows, base_name))

    return {
        name: value
        for name, value in values.items()
        if _is_finite_number(value)
    }


def _sequence_row(
    sample: UnifiedTelemetry,
    previous: UnifiedTelemetry | None,
) -> dict[str, float]:
    return {
        "altitude": sample.altitude_m,
        "vx": _number(sample.velocity_x_m_s),
        "vy": _number(sample.velocity_y_m_s),
        "vz": _number(_vertical_speed(sample)),
        "ground_speed": _ground_speed(sample),
        "roll": _angle_deg(sample.roll_rad),
        "pitch": _angle_deg(sample.pitch_rad),
        "yaw": _yaw_deg(sample),
        "battery_voltage": _number(sample.battery_voltage_v),
        "battery_remaining": _battery_remaining(sample),
        "gps_fix_status": _number(sample.gps_fix_type),
        "satellites_visible": float(_satellites(sample)),
        "eph": _number(sample.gps_eph),
        "epv": _number(sample.gps_epv),
        "position_speed_error": _position_speed_error(previous, sample),
        "altitude_velocity_error": _altitude_velocity_error(previous, sample),
        "heading_yaw_error": _heading_yaw_error(previous, sample),
        "pos_test_ratio": _number(sample.pos_test_ratio),
        "vel_test_ratio": _number(sample.vel_test_ratio),
        "hgt_test_ratio": _number(sample.hgt_test_ratio),
        "mag_test_ratio": _number(sample.mag_test_ratio),
        "hdg_test_ratio": _number(sample.hdg_test_ratio),
        "filter_fault_flags": _number(sample.filter_fault_flags),
        "innovation_check_flags": _number(sample.innovation_check_flags),
        "gps_check_fail_flags": _number(sample.gps_check_fail_flags),
        "attitude_invalid": _number(sample.attitude_invalid),
        "angular_velocity_invalid": _number(sample.angular_velocity_invalid),
        "local_position_invalid": _number(sample.local_position_invalid),
        "global_position_invalid": _number(sample.global_position_invalid),
        "local_velocity_invalid": _number(sample.local_velocity_invalid),
        "battery_warning": _number(sample.battery_warning),
        "fd_motor_failure": _number(sample.fd_motor_failure),
        "fd_critical_failure": _number(sample.fd_critical_failure),
        "fd_roll": _number(sample.fd_roll),
        "fd_pitch": _number(sample.fd_pitch),
        "fd_alt": _number(sample.fd_alt),
        "fd_motor": _number(sample.fd_motor),
        "fd_battery": _number(sample.fd_battery),
        "fd_imbalanced_prop": _number(sample.fd_imbalanced_prop),
    }


def _window_base_feature(feature_name: str, suffix: str) -> str:
    mapped = _WINDOW_BASE_FEATURES.get(feature_name)
    if mapped is not None:
        return mapped
    return feature_name[: -len(suffix)]


def _position_speed_error(
    previous: UnifiedTelemetry | None,
    current: UnifiedTelemetry,
) -> float:
    if previous is None:
        return 0.0
    elapsed_sec = elapsed_seconds(previous, current)
    if elapsed_sec <= 0.02 or elapsed_sec > 2.0:
        return 0.0
    return abs(distance_meters(previous, current) / elapsed_sec - _ground_speed(current))


def _altitude_velocity_error(
    previous: UnifiedTelemetry | None,
    current: UnifiedTelemetry,
) -> float:
    if previous is None:
        return 0.0
    vertical_speed = _vertical_speed(current)
    if vertical_speed is None:
        return 0.0
    elapsed_sec = elapsed_seconds(previous, current)
    if elapsed_sec <= 0.02 or elapsed_sec > 2.0:
        return 0.0
    altitude_delta_m = current.altitude_m - previous.altitude_m
    return abs(altitude_delta_m / elapsed_sec - vertical_speed)


def _heading_yaw_error(
    previous: UnifiedTelemetry | None,
    current: UnifiedTelemetry,
) -> float:
    if previous is None:
        return 0.0
    elapsed_sec = elapsed_seconds(previous, current)
    if elapsed_sec <= 0.02 or elapsed_sec > 2.0:
        return 0.0
    distance_delta_m = distance_meters(previous, current)
    yaw_deg = _yaw_deg_optional(current)
    if distance_delta_m <= 0.5 or yaw_deg is None:
        return 0.0
    heading_deg = _bearing_degrees(previous, current)
    return abs((heading_deg - yaw_deg + 180.0) % 360.0 - 180.0)


def _ground_speed(sample: UnifiedTelemetry) -> float:
    if sample.ground_speed_m_s is not None:
        return float(sample.ground_speed_m_s)
    if sample.velocity_x_m_s is not None and sample.velocity_y_m_s is not None:
        return sqrt(sample.velocity_x_m_s**2 + sample.velocity_y_m_s**2)
    return 0.0


def _vertical_speed(sample: UnifiedTelemetry) -> float | None:
    if sample.velocity_z_m_s is not None:
        return sample.velocity_z_m_s
    return sample.vertical_speed_m_s


def _angle_deg(value: float | None) -> float:
    if value is None:
        return 0.0
    return degrees(value)


def _yaw_deg(sample: UnifiedTelemetry) -> float:
    yaw_deg = _yaw_deg_optional(sample)
    if yaw_deg is None:
        return 0.0
    return yaw_deg


def _yaw_deg_optional(sample: UnifiedTelemetry) -> float | None:
    if sample.yaw_rad is not None:
        return degrees(sample.yaw_rad) % 360.0
    if sample.heading_deg is not None:
        return sample.heading_deg % 360.0
    return None


def _battery_remaining(sample: UnifiedTelemetry) -> float:
    value = float(sample.battery_percent)
    if value > 1.0:
        return value / 100.0
    return value


def _satellites(sample: UnifiedTelemetry) -> int:
    if sample.satellites_visible is not None:
        return sample.satellites_visible
    return sample.satellites


def _bearing_degrees(
    previous: UnifiedTelemetry,
    current: UnifiedTelemetry,
) -> float:
    from math import atan2, cos, radians, sin

    previous_lat = radians(previous.latitude_deg)
    current_lat = radians(current.latitude_deg)
    delta_lon = radians(current.longitude_deg - previous.longitude_deg)
    y = sin(delta_lon) * cos(current_lat)
    x = (
        cos(previous_lat) * sin(current_lat)
        - sin(previous_lat) * cos(current_lat) * cos(delta_lon)
    )
    return (degrees(atan2(y, x)) + 360.0) % 360.0


def _row_values(rows: Sequence[Mapping[str, float]], feature_name: str) -> list[float]:
    return [row.get(feature_name, 0.0) for row in rows]


def _number(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _max(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return max(values)


def _delta(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return values[-1] - values[0]


def _angle_delta(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0] + 180.0) % 360.0 - 180.0


def _is_finite_number(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
