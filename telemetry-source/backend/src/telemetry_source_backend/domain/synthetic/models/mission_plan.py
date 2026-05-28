"""Synthetic mission plan."""

from dataclasses import dataclass, field

from telemetry_source_backend.domain.synthetic.models.battery_profile import (
    BatteryProfile,
)
from telemetry_source_backend.domain.synthetic.models.initial_state import InitialState
from telemetry_source_backend.domain.synthetic.models.mission_phase import MissionPhase
from telemetry_source_backend.domain.synthetic.models.motion_profile import MotionProfile
from telemetry_source_backend.domain.synthetic.models.noise_profile import NoiseProfile


@dataclass(frozen=True, slots=True)
class MissionPlan:
    """Flight plan used by the synthetic source."""

    name: str
    frequency_hz: float
    initial_state: InitialState
    phases: tuple[MissionPhase, ...]
    drone_id: str = "uav-001"
    motion_profile: MotionProfile = field(default_factory=MotionProfile)
    noise_profile: NoiseProfile = field(default_factory=NoiseProfile)
    battery_profile: BatteryProfile = field(default_factory=BatteryProfile)
