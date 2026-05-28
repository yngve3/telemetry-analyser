"""Battery drain model for synthetic missions."""

from dataclasses import dataclass, field

from telemetry_source_backend.domain.synthetic.models import (
    BatteryProfile,
    MissionPlan,
    PhaseType,
)
from telemetry_source_backend.domain.synthetic.services.mission_timeline import (
    MissionTimeline,
)


@dataclass(frozen=True, slots=True)
class BatteryDrainModel:
    """Computes battery level using phase-specific drain rates."""

    timeline: MissionTimeline = field(default_factory=MissionTimeline)

    def battery_percent(
        self,
        plan: MissionPlan,
        elapsed_sec: float,
        duration_overrides: dict[int, float] | None = None,
    ) -> float:
        remaining = plan.initial_state.battery
        elapsed_sec = max(elapsed_sec, 0.0)
        cursor = 0.0

        for index, phase in enumerate(plan.phases):
            duration = self.timeline.phase_duration(plan, index, duration_overrides)
            consumed_duration = min(max(elapsed_sec - cursor, 0.0), duration)
            remaining -= consumed_duration * self._rate(plan.battery_profile, phase.type)
            cursor += duration

            if elapsed_sec <= cursor:
                break

        return min(max(remaining, 0.0), 100.0)

    def _rate(self, profile: BatteryProfile, phase_type: PhaseType) -> float:
        match phase_type:
            case PhaseType.TAKEOFF:
                return profile.takeoff_percent_per_sec
            case PhaseType.WAYPOINT:
                return profile.waypoint_percent_per_sec
            case PhaseType.TURN:
                return profile.turn_percent_per_sec
            case PhaseType.HOVER:
                return profile.hover_percent_per_sec
            case PhaseType.RETURN_HOME:
                return profile.return_home_percent_per_sec
            case PhaseType.LANDING:
                return profile.landing_percent_per_sec

