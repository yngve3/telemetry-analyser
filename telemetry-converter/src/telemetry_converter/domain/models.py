"""DTOs used by telemetry conversion adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class UnifiedTelemetryPayload:
    """Payload matching the shared UnifiedTelemetry contract."""

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

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "timestamp": self.timestamp.isoformat(),
            "drone_id": self.drone_id,
            "latitude_deg": self.latitude_deg,
            "longitude_deg": self.longitude_deg,
            "altitude_m": self.altitude_m,
            "battery_percent": self.battery_percent,
            "satellites": self.satellites,
        }

        optional_values = {
            "ground_speed_m_s": self.ground_speed_m_s,
            "vertical_speed_m_s": self.vertical_speed_m_s,
            "heading_deg": self.heading_deg,
            "relative_altitude_m": self.relative_altitude_m,
            "velocity_x_m_s": self.velocity_x_m_s,
            "velocity_y_m_s": self.velocity_y_m_s,
            "velocity_z_m_s": self.velocity_z_m_s,
            "roll_rad": self.roll_rad,
            "pitch_rad": self.pitch_rad,
            "yaw_rad": self.yaw_rad,
            "roll_rate_rad_s": self.roll_rate_rad_s,
            "pitch_rate_rad_s": self.pitch_rate_rad_s,
            "yaw_rate_rad_s": self.yaw_rate_rad_s,
            "satellites_visible": self.satellites_visible,
            "gps_fix_type": self.gps_fix_type,
            "gps_eph": self.gps_eph,
            "gps_epv": self.gps_epv,
            "battery_voltage_v": self.battery_voltage_v,
            "battery_current_a": self.battery_current_a,
            "system_status": self.system_status,
            "flight_mode": self.flight_mode,
            "armed": self.armed,
            "sensor_health_flags": self.sensor_health_flags,
            "attitude_age_ms": self.attitude_age_ms,
            "position_age_ms": self.position_age_ms,
            "gps_age_ms": self.gps_age_ms,
            "system_age_ms": self.system_age_ms,
            "message_quality": self.message_quality,
            "pos_test_ratio": self.pos_test_ratio,
            "vel_test_ratio": self.vel_test_ratio,
            "hgt_test_ratio": self.hgt_test_ratio,
            "mag_test_ratio": self.mag_test_ratio,
            "hdg_test_ratio": self.hdg_test_ratio,
            "filter_fault_flags": self.filter_fault_flags,
            "innovation_check_flags": self.innovation_check_flags,
            "gps_check_fail_flags": self.gps_check_fail_flags,
            "attitude_invalid": self.attitude_invalid,
            "angular_velocity_invalid": self.angular_velocity_invalid,
            "local_position_invalid": self.local_position_invalid,
            "global_position_invalid": self.global_position_invalid,
            "local_velocity_invalid": self.local_velocity_invalid,
            "battery_warning": self.battery_warning,
            "fd_motor_failure": self.fd_motor_failure,
            "fd_critical_failure": self.fd_critical_failure,
            "fd_roll": self.fd_roll,
            "fd_pitch": self.fd_pitch,
            "fd_alt": self.fd_alt,
            "fd_motor": self.fd_motor,
            "fd_battery": self.fd_battery,
            "fd_imbalanced_prop": self.fd_imbalanced_prop,
        }
        payload.update(
            {
                key: value
                for key, value in optional_values.items()
                if value is not None
            }
        )
        return payload
