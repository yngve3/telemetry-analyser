"""Snapshot source API request schemas."""

from pydantic import BaseModel, Field


class SnapshotSampleRequest(BaseModel):
    timestamp: str
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


class SnapshotCreateRequest(BaseModel):
    name: str
    samples: list[SnapshotSampleRequest] = Field(min_length=1)
    interval_seconds: float = Field(default=1.0, gt=0)
    repeat: bool = False
