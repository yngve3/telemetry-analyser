"""Human-friendly synthetic mission script."""

from dataclasses import dataclass, field

from telemetry_source_backend.domain.synthetic.models import (
    BatteryProfile,
    MotionProfile,
    NoiseProfile,
)
from telemetry_source_backend.domain.synthetic.script.models.script_home import (
    ScriptHome,
)
from telemetry_source_backend.domain.synthetic.script.models.script_step import (
    ScriptStep,
)


@dataclass(frozen=True, slots=True)
class MissionScript:
    """Mission format intended for UI input and JSON import/export."""

    name: str
    frequency_hz: float
    home: ScriptHome
    steps: tuple[ScriptStep, ...]
    drone_id: str = "uav-001"
    motion_profile: MotionProfile = field(default_factory=MotionProfile)
    noise_profile: NoiseProfile = field(default_factory=NoiseProfile)
    battery_profile: BatteryProfile = field(default_factory=BatteryProfile)
