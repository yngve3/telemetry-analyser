"""Human-friendly mission script step."""

from dataclasses import dataclass

from telemetry_source_backend.domain.synthetic.script.models.script_step_type import (
    ScriptStepType,
)
from telemetry_source_backend.domain.synthetic.script.models.turn_direction import (
    TurnDirection,
)


@dataclass(frozen=True, slots=True)
class ScriptStep:
    """One high-level mission step authored by a user."""

    type: ScriptStepType
    target_altitude: float | None = None
    distance_m: float | None = None
    speed_m_s: float | None = None
    direction: TurnDirection | None = None
    angle_deg: float | None = None
    duration_sec: float | None = None

