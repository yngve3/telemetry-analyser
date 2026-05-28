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
