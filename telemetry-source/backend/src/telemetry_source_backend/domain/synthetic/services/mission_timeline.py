"""Synthetic mission timeline service."""

from dataclasses import dataclass

from telemetry_source_backend.domain.exceptions import MissionValidationError
from telemetry_source_backend.domain.synthetic.models import MissionPhase, MissionPlan


@dataclass(frozen=True, slots=True)
class PhaseProgress:
    """Resolved mission phase and local progress for a timestamp."""

    index: int
    phase: MissionPhase
    start_sec: float
    end_sec: float
    progress: float
    is_complete: bool = False


class MissionTimeline:
    """Resolves active mission phases by elapsed time."""

    def total_duration(self, plan: MissionPlan) -> float:
        return sum(phase.duration_sec for phase in plan.phases)

    def phase_duration(
        self,
        plan: MissionPlan,
        index: int,
        duration_overrides: dict[int, float] | None = None,
    ) -> float:
        if duration_overrides is not None and index in duration_overrides:
            return duration_overrides[index]

        return plan.phases[index].duration_sec

    def total_duration_with_overrides(
        self,
        plan: MissionPlan,
        duration_overrides: dict[int, float] | None = None,
    ) -> float:
        return sum(
            self.phase_duration(plan, index, duration_overrides)
            for index in range(len(plan.phases))
        )

    def resolve(
        self,
        plan: MissionPlan,
        elapsed_sec: float,
        duration_overrides: dict[int, float] | None = None,
    ) -> PhaseProgress:
        if elapsed_sec < 0:
            raise MissionValidationError("Elapsed time must not be negative.")

        if not plan.phases:
            raise MissionValidationError("Mission plan must contain at least one phase.")

        total = self.total_duration_with_overrides(plan, duration_overrides)
        if elapsed_sec >= total:
            last_duration = self.phase_duration(
                plan,
                len(plan.phases) - 1,
                duration_overrides,
            )
            start = total - last_duration
            return PhaseProgress(
                index=len(plan.phases) - 1,
                phase=plan.phases[-1],
                start_sec=start,
                end_sec=total,
                progress=1.0,
                is_complete=True,
            )

        cursor = 0.0
        for index, phase in enumerate(plan.phases):
            duration = self.phase_duration(plan, index, duration_overrides)
            phase_end = cursor + duration
            if elapsed_sec < phase_end:
                progress = (elapsed_sec - cursor) / duration
                return PhaseProgress(
                    index=index,
                    phase=phase,
                    start_sec=cursor,
                    end_sec=phase_end,
                    progress=min(max(progress, 0.0), 1.0),
                )
            cursor = phase_end

        raise AssertionError("Timeline resolution should have returned a phase.")
