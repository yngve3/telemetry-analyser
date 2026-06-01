"""Analysis request schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class TelemetryPayloadFormat(StrEnum):
    UNIFIED_TELEMETRY = "unified.telemetry"
    MAVLINK_V2 = "mavlink.v2"


class UnifiedTelemetryRequest(BaseModel):
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
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: TelemetryPayloadFormat = TelemetryPayloadFormat.UNIFIED_TELEMETRY
    telemetry: dict[str, Any] | None = None
    payload_base64: str | None = None
