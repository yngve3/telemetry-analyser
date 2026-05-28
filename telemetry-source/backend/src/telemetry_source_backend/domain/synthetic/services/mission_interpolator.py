"""Synthetic mission interpolation service."""

from __future__ import annotations

from dataclasses import dataclass, field

from telemetry_source_backend.domain.synthetic.models import MissionPlan
from telemetry_source_backend.domain.synthetic.models import PhaseType
from telemetry_source_backend.domain.synthetic.services import geodesy
from telemetry_source_backend.domain.synthetic.services.battery_drain_model import (
    BatteryDrainModel,
)
from telemetry_source_backend.domain.synthetic.services.mission_timeline import (
    MissionTimeline,
    PhaseProgress,
)
from telemetry_source_backend.domain.synthetic.services.motion_profile_solver import (
    MotionProfileSolver,
)


@dataclass(frozen=True, slots=True)
class MissionKinematicState:
    """Interpolated UAV state at a point in mission time."""

    latitude: float
    longitude: float
    altitude: float
    battery: float
    heading_deg: float
    ground_speed_m_s: float
    vertical_speed_m_s: float
    active_phase_index: int
    is_complete: bool


@dataclass(frozen=True, slots=True)
class MissionInterpolator:
    """Interpolates mission state inside the active phase."""

    timeline: MissionTimeline = field(default_factory=MissionTimeline)
    motion_solver: MotionProfileSolver = field(default_factory=MotionProfileSolver)
    battery_model: BatteryDrainModel = field(default_factory=BatteryDrainModel)

    def interpolate(
        self,
        plan: MissionPlan,
        elapsed_sec: float,
        duration_overrides: dict[int, float] | None = None,
        speed_overrides: dict[int, float] | None = None,
    ) -> MissionKinematicState:
        phase_progress = self.timeline.resolve(plan, elapsed_sec, duration_overrides)
        start_state = self._state_at_phase_start(plan, phase_progress)
        phase = phase_progress.phase
        phase_duration = self.timeline.phase_duration(
            plan,
            phase_progress.index,
            duration_overrides,
        )

        target_latitude = (
            phase.target_latitude
            if phase.target_latitude is not None
            else start_state.latitude
        )
        target_longitude = (
            phase.target_longitude
            if phase.target_longitude is not None
            else start_state.longitude
        )
        target_altitude = (
            phase.target_altitude
            if phase.target_altitude is not None
            else start_state.altitude
        )
        target_heading = (
            phase.target_heading_deg
            if phase.target_heading_deg is not None
            else start_state.heading_deg
        )

        progress = self._motion_progress(
            plan,
            start_state,
            phase_progress,
            phase_duration,
            speed_overrides,
        )
        altitude_delta = target_altitude - start_state.altitude

        return MissionKinematicState(
            latitude=self._lerp(start_state.latitude, target_latitude, progress),
            longitude=self._lerp(start_state.longitude, target_longitude, progress),
            altitude=self._lerp(start_state.altitude, target_altitude, progress),
            battery=self.battery_model.battery_percent(
                plan,
                elapsed_sec,
                duration_overrides,
            ),
            heading_deg=self._interpolate_heading(
                start_state.heading_deg,
                target_heading,
                progress,
            ),
            ground_speed_m_s=self._phase_speed(
                phase.target_speed,
                phase_progress.index,
                speed_overrides,
            ),
            vertical_speed_m_s=altitude_delta / phase_duration,
            active_phase_index=phase_progress.index,
            is_complete=phase_progress.is_complete,
        )

    def _state_at_phase_start(
        self,
        plan: MissionPlan,
        phase_progress: PhaseProgress,
    ) -> MissionKinematicState:
        latitude = plan.initial_state.latitude
        longitude = plan.initial_state.longitude
        altitude = plan.initial_state.altitude
        heading = plan.initial_state.heading_deg

        for phase in plan.phases[: phase_progress.index]:
            latitude = (
                phase.target_latitude if phase.target_latitude is not None else latitude
            )
            longitude = (
                phase.target_longitude
                if phase.target_longitude is not None
                else longitude
            )
            altitude = (
                phase.target_altitude
                if phase.target_altitude is not None
                else altitude
            )
            heading = (
                phase.target_heading_deg
                if phase.target_heading_deg is not None
                else heading
            )

        return MissionKinematicState(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            battery=max(
                0.0,
                plan.initial_state.battery
                - 0.0,
            ),
            heading_deg=heading,
            ground_speed_m_s=0.0,
            vertical_speed_m_s=0.0,
            active_phase_index=phase_progress.index,
            is_complete=phase_progress.is_complete,
        )

    def _lerp(self, start: float, end: float, progress: float) -> float:
        return start + (end - start) * progress

    def _interpolate_heading(
        self,
        start_heading: float,
        target_heading: float,
        progress: float,
    ) -> float:
        delta = ((target_heading - start_heading + 540) % 360) - 180
        return (start_heading + delta * progress) % 360

    def _motion_progress(
        self,
        plan: MissionPlan,
        start_state: MissionKinematicState,
        phase_progress: PhaseProgress,
        phase_duration: float,
        speed_overrides: dict[int, float] | None,
    ) -> float:
        phase = phase_progress.phase
        if phase.type not in {PhaseType.WAYPOINT, PhaseType.RETURN_HOME}:
            return phase_progress.progress

        target_latitude = (
            phase.target_latitude
            if phase.target_latitude is not None
            else start_state.latitude
        )
        target_longitude = (
            phase.target_longitude
            if phase.target_longitude is not None
            else start_state.longitude
        )
        distance_m = geodesy.distance(
            start_state.latitude,
            start_state.longitude,
            target_latitude,
            target_longitude,
        )
        effective_speed = self._phase_speed(
            phase.target_speed,
            phase_progress.index,
            speed_overrides,
        )
        if distance_m <= 0 or not effective_speed:
            return phase_progress.progress

        elapsed_in_phase = phase_progress.progress * phase_duration
        return self.motion_solver.progress(
            elapsed_in_phase,
            phase_duration,
            distance_m,
            effective_speed,
            plan.motion_profile.horizontal_acceleration_m_s2,
        )

    def _phase_speed(
        self,
        target_speed: float | None,
        phase_index: int,
        speed_overrides: dict[int, float] | None,
    ) -> float:
        if speed_overrides is not None and phase_index in speed_overrides:
            return speed_overrides[phase_index]

        return target_speed or 0.0
