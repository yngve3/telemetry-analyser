"""Synthetic source API request schemas."""

from typing import Any

from pydantic import BaseModel, Field

from telemetry_source_backend.domain.synthetic.models import CommandType
from telemetry_source_backend.domain.synthetic.script.models import (
    ScriptStepType,
    TurnDirection,
)


class ScriptHomeRequest(BaseModel):
    latitude: float
    longitude: float
    altitude: float = 0.0
    heading_deg: float = 0.0
    battery: float = 100.0


class ScriptStepRequest(BaseModel):
    type: ScriptStepType
    target_altitude: float | None = None
    distance_m: float | None = None
    speed_m_s: float | None = None
    direction: TurnDirection | None = None
    angle_deg: float | None = None
    duration_sec: float | None = None


class MotionProfileRequest(BaseModel):
    horizontal_acceleration_m_s2: float = Field(default=2.0, gt=0)
    default_climb_rate_m_s: float = Field(default=3.0, gt=0)
    default_descent_rate_m_s: float = Field(default=2.0, gt=0)
    default_yaw_rate_deg_s: float = Field(default=45.0, gt=0)
    default_return_speed_m_s: float = Field(default=8.0, gt=0)


class NoiseProfileRequest(BaseModel):
    random_seed: int | None = None
    gps_position_std_m: float = Field(default=0.0, ge=0)
    altitude_std_m: float = Field(default=0.0, ge=0)
    speed_std_m_s: float = Field(default=0.0, ge=0)
    heading_std_deg: float = Field(default=0.0, ge=0)
    battery_std_percent: float = Field(default=0.0, ge=0)


class BatteryProfileRequest(BaseModel):
    takeoff_percent_per_sec: float = Field(default=0.025, ge=0)
    waypoint_percent_per_sec: float = Field(default=0.015, ge=0)
    turn_percent_per_sec: float = Field(default=0.010, ge=0)
    hover_percent_per_sec: float = Field(default=0.012, ge=0)
    return_home_percent_per_sec: float = Field(default=0.015, ge=0)
    landing_percent_per_sec: float = Field(default=0.010, ge=0)


class MissionScriptRequest(BaseModel):
    name: str
    frequency_hz: float = Field(gt=0)
    home: ScriptHomeRequest
    steps: list[ScriptStepRequest]
    drone_id: str = "uav-001"
    motion_profile: MotionProfileRequest = Field(default_factory=MotionProfileRequest)
    noise_profile: NoiseProfileRequest = Field(default_factory=NoiseProfileRequest)
    battery_profile: BatteryProfileRequest = Field(default_factory=BatteryProfileRequest)


class MissionCommandRequest(BaseModel):
    command: CommandType
    type: str | None = None
    start_after_sec: float | None = None
    duration_sec: float | None = None
    intensity: float | None = None
    name: str | None = None
    value: Any = None


class TickRequest(BaseModel):
    delta_sec: float | None = Field(default=None, gt=0)


class UdpStreamRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=14550, ge=1, le=65535)
    frequency_hz: float | None = Field(default=None, gt=0)
    repeat: bool | None = None
