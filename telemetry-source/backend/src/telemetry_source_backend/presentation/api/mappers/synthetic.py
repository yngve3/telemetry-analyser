"""Mappers for synthetic source API schemas."""

from typing import Any

from telemetry_source_backend.application.ports import TelemetryValidator
from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.infrastructure.contracts.telemetry_contract import (
    telemetry_sample_to_contract_dict,
)
from telemetry_source_backend.domain.synthetic.models import MissionCommand
from telemetry_source_backend.domain.synthetic.models import (
    BatteryProfile,
    MotionProfile,
    NoiseProfile,
)
from telemetry_source_backend.domain.synthetic.script.models import (
    MissionScript,
    ScriptHome,
    ScriptStep,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_synthetic_mission_registry import (
    SyntheticMissionRecord,
)
from telemetry_source_backend.presentation.api.schemas.synthetic_requests import (
    MissionCommandRequest,
    MissionScriptRequest,
)
from telemetry_source_backend.presentation.api.schemas.synthetic_responses import (
    MissionListItemResponse,
    MissionStatusResponse,
    TelemetrySampleResponse,
)


def mission_script_from_request(request: MissionScriptRequest) -> MissionScript:
    return MissionScript(
        name=request.name,
        frequency_hz=request.frequency_hz,
        home=ScriptHome(
            latitude=request.home.latitude,
            longitude=request.home.longitude,
            altitude=request.home.altitude,
            heading_deg=request.home.heading_deg,
            battery=request.home.battery,
        ),
        steps=tuple(
            ScriptStep(
                type=step.type,
                target_altitude=step.target_altitude,
                distance_m=step.distance_m,
                speed_m_s=step.speed_m_s,
                direction=step.direction,
                angle_deg=step.angle_deg,
                duration_sec=step.duration_sec,
            )
            for step in request.steps
        ),
        drone_id=request.drone_id,
        motion_profile=MotionProfile(
            horizontal_acceleration_m_s2=(
                request.motion_profile.horizontal_acceleration_m_s2
            ),
            default_climb_rate_m_s=request.motion_profile.default_climb_rate_m_s,
            default_descent_rate_m_s=(
                request.motion_profile.default_descent_rate_m_s
            ),
            default_yaw_rate_deg_s=request.motion_profile.default_yaw_rate_deg_s,
            default_return_speed_m_s=request.motion_profile.default_return_speed_m_s,
        ),
        noise_profile=NoiseProfile(
            random_seed=request.noise_profile.random_seed,
            gps_position_std_m=request.noise_profile.gps_position_std_m,
            altitude_std_m=request.noise_profile.altitude_std_m,
            speed_std_m_s=request.noise_profile.speed_std_m_s,
            heading_std_deg=request.noise_profile.heading_std_deg,
            battery_std_percent=request.noise_profile.battery_std_percent,
        ),
        battery_profile=BatteryProfile(
            takeoff_percent_per_sec=request.battery_profile.takeoff_percent_per_sec,
            waypoint_percent_per_sec=request.battery_profile.waypoint_percent_per_sec,
            turn_percent_per_sec=request.battery_profile.turn_percent_per_sec,
            hover_percent_per_sec=request.battery_profile.hover_percent_per_sec,
            return_home_percent_per_sec=(
                request.battery_profile.return_home_percent_per_sec
            ),
            landing_percent_per_sec=request.battery_profile.landing_percent_per_sec,
        ),
    )


def mission_command_from_request(request: MissionCommandRequest) -> MissionCommand:
    parameters: dict[str, Any] = {}
    for key in (
        "type",
        "start_after_sec",
        "duration_sec",
        "intensity",
        "name",
        "value",
    ):
        value = getattr(request, key)
        if value is not None:
            parameters[key] = value

    return MissionCommand(command=request.command, parameters=parameters)


def telemetry_sample_response(
    sample: TelemetrySample,
    validator: TelemetryValidator,
) -> TelemetrySampleResponse:
    payload = telemetry_sample_to_contract_dict(sample)
    validator.validate_payload(payload)
    return TelemetrySampleResponse(**payload)


def mission_status_response(record: SyntheticMissionRecord) -> MissionStatusResponse:
    runner = record.runner
    return MissionStatusResponse(
        mission_id=record.mission_id,
        name=record.plan.name,
        frequency_hz=record.plan.frequency_hz,
        elapsed_sec=runner.state.elapsed_sec,
        total_duration_sec=runner.timeline.total_duration(record.plan),
        active_phase_index=runner.state.active_phase_index,
        is_running=runner.state.is_running,
        is_completed=runner.is_completed,
        scheduled_anomalies_count=len(runner.state.scheduled_anomalies),
    )


def mission_list_item_response(
    record: SyntheticMissionRecord,
) -> MissionListItemResponse:
    return MissionListItemResponse(
        mission_id=record.mission_id,
        name=record.plan.name,
        frequency_hz=record.plan.frequency_hz,
        is_running=record.runner.state.is_running,
        is_completed=record.runner.is_completed,
    )
