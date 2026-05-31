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
        }
        payload.update(
            {
                key: value
                for key, value in optional_values.items()
                if value is not None
            }
        )
        return payload
