"""Compiler from human-friendly mission scripts to executable mission plans."""

from __future__ import annotations

from dataclasses import dataclass, field

from telemetry_source_backend.domain.synthetic.models import (
    InitialState,
    MissionPhase,
    MissionPlan,
    PhaseType,
)
from telemetry_source_backend.domain.synthetic.script.models import (
    MissionScript,
    ScriptStep,
    ScriptStepType,
    TurnDirection,
)
from telemetry_source_backend.domain.synthetic.script.services.mission_script_validator import (
    MissionScriptValidator,
)
from telemetry_source_backend.domain.synthetic.services import geodesy
from telemetry_source_backend.domain.synthetic.services.motion_profile_solver import (
    MotionProfileSolver,
)


@dataclass(slots=True)
class _CompilerState:
    latitude: float
    longitude: float
    altitude: float
    heading_deg: float


@dataclass(frozen=True, slots=True)
class MissionScriptCompiler:
    """Converts a `MissionScript` into the generator's executable `MissionPlan`."""

    validator: MissionScriptValidator = field(default_factory=MissionScriptValidator)
    motion_solver: MotionProfileSolver = field(default_factory=MotionProfileSolver)

    def compile(self, script: MissionScript) -> MissionPlan:
        self.validator.validate(script)

        state = _CompilerState(
            latitude=script.home.latitude,
            longitude=script.home.longitude,
            altitude=script.home.altitude,
            heading_deg=geodesy.normalize_heading(script.home.heading_deg),
        )
        phases: list[MissionPhase] = []

        for step in script.steps:
            phase = self._compile_step(script, state, step)
            phases.append(phase)
            self._apply_phase_target(state, phase)

        return MissionPlan(
            name=script.name,
            frequency_hz=script.frequency_hz,
            initial_state=InitialState(
                latitude=script.home.latitude,
                longitude=script.home.longitude,
                altitude=script.home.altitude,
                battery=script.home.battery,
                heading_deg=geodesy.normalize_heading(script.home.heading_deg),
            ),
            phases=tuple(phases),
            drone_id=script.drone_id,
            motion_profile=script.motion_profile,
            noise_profile=script.noise_profile,
            battery_profile=script.battery_profile,
        )

    def _compile_step(
        self,
        script: MissionScript,
        state: _CompilerState,
        step: ScriptStep,
    ) -> MissionPhase:
        match step.type:
            case ScriptStepType.TAKEOFF:
                target_altitude = self._required(step.target_altitude)
                duration_sec = max(
                    abs(target_altitude - state.altitude)
                    / script.motion_profile.default_climb_rate_m_s,
                    0.1,
                )
                return MissionPhase(
                    type=PhaseType.TAKEOFF,
                    duration_sec=duration_sec,
                    target_latitude=state.latitude,
                    target_longitude=state.longitude,
                    target_altitude=target_altitude,
                    target_heading_deg=state.heading_deg,
                )
            case ScriptStepType.MOVE_FORWARD:
                distance_m = self._required(step.distance_m)
                speed_m_s = self._required(step.speed_m_s)
                target_latitude, target_longitude = geodesy.move(
                    latitude=state.latitude,
                    longitude=state.longitude,
                    heading_deg=state.heading_deg,
                    distance_m=distance_m,
                )
                return MissionPhase(
                    type=PhaseType.WAYPOINT,
                    duration_sec=self.motion_solver.duration_for_distance(
                        distance_m,
                        speed_m_s,
                        script.motion_profile.horizontal_acceleration_m_s2,
                    ),
                    target_latitude=target_latitude,
                    target_longitude=target_longitude,
                    target_altitude=state.altitude,
                    target_speed=speed_m_s,
                    target_heading_deg=state.heading_deg,
                )
            case ScriptStepType.TURN:
                angle_deg = self._required(step.angle_deg)
                direction = step.direction or TurnDirection.RIGHT
                signed_angle = angle_deg if direction is TurnDirection.RIGHT else -angle_deg
                target_heading = geodesy.normalize_heading(
                    state.heading_deg + signed_angle
                )
                return MissionPhase(
                    type=PhaseType.TURN,
                    duration_sec=max(
                        angle_deg / script.motion_profile.default_yaw_rate_deg_s,
                        0.1,
                    ),
                    target_latitude=state.latitude,
                    target_longitude=state.longitude,
                    target_altitude=state.altitude,
                    target_speed=0.0,
                    target_heading_deg=target_heading,
                )
            case ScriptStepType.HOVER:
                duration_sec = self._required(step.duration_sec)
                return MissionPhase(
                    type=PhaseType.HOVER,
                    duration_sec=duration_sec,
                    target_latitude=state.latitude,
                    target_longitude=state.longitude,
                    target_altitude=state.altitude,
                    target_speed=0.0,
                    target_heading_deg=state.heading_deg,
                )
            case ScriptStepType.RETURN_HOME:
                distance_m = geodesy.distance(
                    state.latitude,
                    state.longitude,
                    script.home.latitude,
                    script.home.longitude,
                )
                speed_m_s = (
                    step.speed_m_s or script.motion_profile.default_return_speed_m_s
                )
                heading = geodesy.bearing(
                    state.latitude,
                    state.longitude,
                    script.home.latitude,
                    script.home.longitude,
                )
                return MissionPhase(
                    type=PhaseType.RETURN_HOME,
                    duration_sec=max(
                        self.motion_solver.duration_for_distance(
                            distance_m,
                            speed_m_s,
                            script.motion_profile.horizontal_acceleration_m_s2,
                        ),
                        0.1,
                    ),
                    target_latitude=script.home.latitude,
                    target_longitude=script.home.longitude,
                    target_altitude=state.altitude,
                    target_speed=speed_m_s,
                    target_heading_deg=heading,
                )
            case ScriptStepType.LANDING:
                duration_sec = max(
                    abs(state.altitude - script.home.altitude)
                    / script.motion_profile.default_descent_rate_m_s,
                    0.1,
                )
                return MissionPhase(
                    type=PhaseType.LANDING,
                    duration_sec=duration_sec,
                    target_latitude=state.latitude,
                    target_longitude=state.longitude,
                    target_altitude=script.home.altitude,
                    target_speed=0.0,
                    target_heading_deg=state.heading_deg,
                )

    def _apply_phase_target(
        self,
        state: _CompilerState,
        phase: MissionPhase,
    ) -> None:
        state.latitude = (
            phase.target_latitude
            if phase.target_latitude is not None
            else state.latitude
        )
        state.longitude = (
            phase.target_longitude
            if phase.target_longitude is not None
            else state.longitude
        )
        state.altitude = (
            phase.target_altitude
            if phase.target_altitude is not None
            else state.altitude
        )
        state.heading_deg = (
            phase.target_heading_deg
            if phase.target_heading_deg is not None
            else state.heading_deg
        )

    def _required(self, value: float | None) -> float:
        if value is None:
            raise AssertionError("Required value was validated before compilation.")
        return value
