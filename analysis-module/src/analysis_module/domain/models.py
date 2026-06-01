"""Telemetry models used by the analysis module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UnifiedTelemetry:
    """Internal telemetry representation consumed by the analysis module."""

    timestamp: datetime
    drone_id: str
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    battery_percent: float
    satellites: int
    ground_speed_m_s: float | None = None
    vertical_speed_m_s: float | None = None
    heading_deg: float | None = None
    relative_altitude_m: float | None = None
    velocity_x_m_s: float | None = None
    velocity_y_m_s: float | None = None
    velocity_z_m_s: float | None = None
    roll_rad: float | None = None
    pitch_rad: float | None = None
    yaw_rad: float | None = None
    roll_rate_rad_s: float | None = None
    pitch_rate_rad_s: float | None = None
    yaw_rate_rad_s: float | None = None
    satellites_visible: int | None = None
    gps_fix_type: int | None = None
    gps_eph: float | None = None
    gps_epv: float | None = None
    battery_voltage_v: float | None = None
    battery_current_a: float | None = None
    system_status: str | None = None
    flight_mode: str | None = None
    armed: bool | None = None
    sensor_health_flags: int | None = None
    attitude_age_ms: int | None = None
    position_age_ms: int | None = None
    gps_age_ms: int | None = None
    system_age_ms: int | None = None
    message_quality: float | None = None
    pos_test_ratio: float | None = None
    vel_test_ratio: float | None = None
    hgt_test_ratio: float | None = None
    mag_test_ratio: float | None = None
    hdg_test_ratio: float | None = None
    filter_fault_flags: int | None = None
    innovation_check_flags: int | None = None
    gps_check_fail_flags: int | None = None
    attitude_invalid: int | None = None
    angular_velocity_invalid: int | None = None
    local_position_invalid: int | None = None
    global_position_invalid: int | None = None
    local_velocity_invalid: int | None = None
    battery_warning: int | None = None
    fd_motor_failure: int | None = None
    fd_critical_failure: int | None = None
    fd_roll: int | None = None
    fd_pitch: int | None = None
    fd_alt: int | None = None
    fd_motor: int | None = None
    fd_battery: int | None = None
    fd_imbalanced_prop: int | None = None
