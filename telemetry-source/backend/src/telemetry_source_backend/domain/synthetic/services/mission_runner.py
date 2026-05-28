"""Synthetic mission runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import (
    MissionCommand,
    MissionPlan,
    MissionRuntimeState,
    PhaseType,
)
from telemetry_source_backend.domain.synthetic.services import geodesy
from telemetry_source_backend.domain.synthetic.services.mission_command_handler import (
    MissionCommandHandler,
)
from telemetry_source_backend.domain.synthetic.services.mission_timeline import (
    MissionTimeline,
)
from telemetry_source_backend.domain.synthetic.services.motion_profile_solver import (
    MotionProfileSolver,
)
from telemetry_source_backend.domain.synthetic.services.synthetic_telemetry_factory import (
    SyntheticTelemetryFactory,
)


@dataclass(slots=True)
class MissionRunner:
    """Coordinates mission playback state."""

    plan: MissionPlan
    mission_id: str = field(default_factory=lambda: str(uuid4()))
    factory: SyntheticTelemetryFactory = field(default_factory=SyntheticTelemetryFactory)
    command_handler: MissionCommandHandler = field(default_factory=MissionCommandHandler)
    timeline: MissionTimeline = field(default_factory=MissionTimeline)
    motion_solver: MotionProfileSolver = field(default_factory=MotionProfileSolver)
    state: MissionRuntimeState = field(init=False)

    def __post_init__(self) -> None:
        self.state = MissionRuntimeState(mission_id=self.mission_id)

    def start(self) -> None:
        self.state.elapsed_sec = 0.0
        self.state.active_phase_index = 0
        self.state.is_running = True

    def pause(self) -> None:
        self.state.is_running = False

    def resume(self) -> None:
        self.state.is_running = True

    def stop(self) -> None:
        self.state.elapsed_sec = 0.0
        self.state.active_phase_index = 0
        self.state.is_running = False

    def submit_command(self, command: MissionCommand) -> None:
        self.command_handler.handle(self.state, command)
        if (
            command.command.value == "set_parameter"
            and command.parameters.get("name") == "target_speed"
        ):
            self._recalculate_target_speed(float(command.parameters["value"]))

    def sample(self, timestamp: datetime | None = None) -> TelemetrySample:
        active_anomalies = [
            scheduled.profile
            for scheduled in self.state.scheduled_anomalies
            if scheduled.is_active_at(self.state.elapsed_sec)
        ]
        sample = self.factory.create_sample(
            self.plan,
            elapsed_sec=self.state.elapsed_sec,
            active_anomalies=active_anomalies,
            timestamp=timestamp,
            duration_overrides=self.state.phase_duration_overrides,
            speed_overrides=self.state.phase_speed_overrides,
        )
        return sample

    def tick(
        self,
        delta_sec: float,
        timestamp: datetime | None = None,
    ) -> TelemetrySample:
        if self.state.is_running:
            total_duration = self.timeline.total_duration_with_overrides(
                self.plan,
                self.state.phase_duration_overrides,
            )
            self.state.elapsed_sec = min(
                self.state.elapsed_sec + max(delta_sec, 0.0),
                total_duration,
            )
            resolved = self.timeline.resolve(
                self.plan,
                self.state.elapsed_sec,
                self.state.phase_duration_overrides,
            )
            self.state.active_phase_index = resolved.index
            if resolved.is_complete:
                self.state.is_running = False

        return self.sample(timestamp=timestamp)

    @property
    def is_completed(self) -> bool:
        return self.state.elapsed_sec >= self.timeline.total_duration_with_overrides(
            self.plan,
            self.state.phase_duration_overrides,
        )

    def _recalculate_target_speed(self, target_speed_m_s: float) -> None:
        if target_speed_m_s <= 0:
            return

        for index, phase in enumerate(self.plan.phases):
            if index < self.state.active_phase_index:
                continue

            if phase.type not in {PhaseType.WAYPOINT, PhaseType.RETURN_HOME}:
                continue

            if index == self.state.active_phase_index:
                distance_m = self._remaining_phase_distance(index)
                elapsed_before_phase = self._elapsed_at_phase_start(index)
                elapsed_in_phase = max(0.0, self.state.elapsed_sec - elapsed_before_phase)
            else:
                distance_m = self._phase_distance(index)
                elapsed_in_phase = 0.0

            if distance_m <= 0:
                continue

            self.state.phase_speed_overrides[index] = target_speed_m_s
            self.state.phase_duration_overrides[index] = (
                elapsed_in_phase
                +
                self.motion_solver.duration_for_distance(
                    distance_m,
                    target_speed_m_s,
                    self.plan.motion_profile.horizontal_acceleration_m_s2,
                )
            )

    def _phase_distance(self, phase_index: int) -> float:
        phase = self.plan.phases[phase_index]
        start_latitude, start_longitude = self._phase_start_position(phase_index)

        if phase.target_latitude is None or phase.target_longitude is None:
            return 0.0

        return geodesy.distance(
            start_latitude,
            start_longitude,
            phase.target_latitude,
            phase.target_longitude,
        )

    def _remaining_phase_distance(self, phase_index: int) -> float:
        phase = self.plan.phases[phase_index]
        if phase.target_latitude is None or phase.target_longitude is None:
            return 0.0

        current_state = self.factory.interpolator.interpolate(
            self.plan,
            self.state.elapsed_sec,
            self.state.phase_duration_overrides,
            self.state.phase_speed_overrides,
        )
        return geodesy.distance(
            current_state.latitude,
            current_state.longitude,
            phase.target_latitude,
            phase.target_longitude,
        )

    def _phase_start_position(self, phase_index: int) -> tuple[float, float]:
        latitude = self.plan.initial_state.latitude
        longitude = self.plan.initial_state.longitude

        for previous in self.plan.phases[:phase_index]:
            if previous.target_latitude is not None:
                latitude = previous.target_latitude
            if previous.target_longitude is not None:
                longitude = previous.target_longitude

        return latitude, longitude

    def _elapsed_at_phase_start(self, phase_index: int) -> float:
        return sum(
            self.timeline.phase_duration(
                self.plan,
                index,
                self.state.phase_duration_overrides,
            )
            for index in range(phase_index)
        )
