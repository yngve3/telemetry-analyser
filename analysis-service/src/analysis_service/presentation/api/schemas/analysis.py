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

    def to_dict(self) -> dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: TelemetryPayloadFormat = TelemetryPayloadFormat.UNIFIED_TELEMETRY
    telemetry: dict[str, Any] | None = None
    payload_base64: str | None = None
