"""Source configuration routes."""

from fastapi import APIRouter, HTTPException, Query, status

from telemetry_source_backend.domain.exceptions import (
    MissionCommandError,
    MissionValidationError,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_synthetic_mission_registry import (
    InMemorySyntheticMissionRegistry,
    SyntheticMissionRecord,
)
from telemetry_source_backend.presentation.api.dependencies import (
    SyntheticMissionBuilderDep,
    SyntheticMissionRegistryDep,
    TelemetryValidatorDep,
)
from telemetry_source_backend.presentation.api.mappers.synthetic import (
    mission_command_from_request,
    mission_list_item_response,
    mission_script_from_request,
    mission_status_response,
    telemetry_sample_response,
)
from telemetry_source_backend.presentation.api.schemas.synthetic_requests import (
    MissionCommandRequest,
    MissionScriptRequest,
    TickRequest,
)
from telemetry_source_backend.presentation.api.schemas.synthetic_responses import (
    MissionCreatedResponse,
    MissionListItemResponse,
    MissionStatusResponse,
    TelemetrySampleResponse,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post(
    "/synthetic/missions",
    response_model=MissionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a synthetic mission",
)
async def create_synthetic_mission(
    request: MissionScriptRequest,
    registry: SyntheticMissionRegistryDep,
    mission_builder: SyntheticMissionBuilderDep,
) -> MissionCreatedResponse:
    try:
        script = mission_script_from_request(request)
        record = mission_builder.build(script)
    except MissionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    registry.save(record)

    return MissionCreatedResponse(
        mission_id=record.mission_id,
        status=mission_status_response(record),
    )


@router.get(
    "/synthetic/missions",
    response_model=list[MissionListItemResponse],
    summary="List synthetic missions",
)
async def list_synthetic_missions(
    registry: SyntheticMissionRegistryDep,
) -> list[MissionListItemResponse]:
    return [mission_list_item_response(record) for record in registry.list()]


@router.get(
    "/synthetic/missions/{mission_id}",
    response_model=MissionStatusResponse,
    summary="Get synthetic mission status",
)
async def get_synthetic_mission_status(
    mission_id: str,
    registry: SyntheticMissionRegistryDep,
) -> MissionStatusResponse:
    record = _get_record_or_404(registry, mission_id)
    return mission_status_response(record)


@router.post(
    "/synthetic/missions/{mission_id}/start",
    response_model=MissionStatusResponse,
    summary="Start a synthetic mission",
)
async def start_synthetic_mission(
    mission_id: str,
    registry: SyntheticMissionRegistryDep,
) -> MissionStatusResponse:
    record = _get_record_or_404(registry, mission_id)
    record.runner.start()
    return mission_status_response(record)


@router.post(
    "/synthetic/missions/{mission_id}/pause",
    response_model=MissionStatusResponse,
    summary="Pause a synthetic mission",
)
async def pause_synthetic_mission(
    mission_id: str,
    registry: SyntheticMissionRegistryDep,
) -> MissionStatusResponse:
    record = _get_record_or_404(registry, mission_id)
    record.runner.pause()
    return mission_status_response(record)


@router.post(
    "/synthetic/missions/{mission_id}/resume",
    response_model=MissionStatusResponse,
    summary="Resume a synthetic mission",
)
async def resume_synthetic_mission(
    mission_id: str,
    registry: SyntheticMissionRegistryDep,
) -> MissionStatusResponse:
    record = _get_record_or_404(registry, mission_id)
    record.runner.resume()
    return mission_status_response(record)


@router.post(
    "/synthetic/missions/{mission_id}/stop",
    response_model=MissionStatusResponse,
    summary="Stop a synthetic mission",
)
async def stop_synthetic_mission(
    mission_id: str,
    registry: SyntheticMissionRegistryDep,
) -> MissionStatusResponse:
    record = _get_record_or_404(registry, mission_id)
    record.runner.stop()
    return mission_status_response(record)


@router.post(
    "/synthetic/missions/{mission_id}/commands",
    response_model=MissionStatusResponse,
    summary="Submit a command to a synthetic mission",
)
async def submit_synthetic_mission_command(
    mission_id: str,
    request: MissionCommandRequest,
    registry: SyntheticMissionRegistryDep,
) -> MissionStatusResponse:
    record = _get_record_or_404(registry, mission_id)

    try:
        record.runner.submit_command(mission_command_from_request(request))
    except (MissionCommandError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return mission_status_response(record)


@router.get(
    "/synthetic/missions/{mission_id}/sample",
    response_model=TelemetrySampleResponse,
    summary="Get current synthetic telemetry sample",
)
async def get_current_synthetic_sample(
    mission_id: str,
    registry: SyntheticMissionRegistryDep,
    validator: TelemetryValidatorDep,
) -> TelemetrySampleResponse:
    record = _get_record_or_404(registry, mission_id)
    return telemetry_sample_response(record.runner.sample(), validator)


@router.post(
    "/synthetic/missions/{mission_id}/sample/next",
    response_model=TelemetrySampleResponse,
    summary="Advance mission time and get next synthetic telemetry sample",
)
async def get_next_synthetic_sample(
    mission_id: str,
    registry: SyntheticMissionRegistryDep,
    validator: TelemetryValidatorDep,
    request: TickRequest | None = None,
) -> TelemetrySampleResponse:
    record = _get_record_or_404(registry, mission_id)
    delta_sec = (
        request.delta_sec
        if request is not None and request.delta_sec is not None
        else 1.0 / record.plan.frequency_hz
    )
    return telemetry_sample_response(record.runner.tick(delta_sec), validator)


@router.get(
    "/synthetic/missions/{mission_id}/samples",
    response_model=list[TelemetrySampleResponse],
    summary="Generate a batch of synthetic telemetry samples",
)
async def get_synthetic_sample_batch(
    mission_id: str,
    registry: SyntheticMissionRegistryDep,
    validator: TelemetryValidatorDep,
    count: int = Query(default=10, ge=1, le=500),
    delta_sec: float | None = Query(default=None, gt=0),
) -> list[TelemetrySampleResponse]:
    record = _get_record_or_404(registry, mission_id)
    step = delta_sec or 1.0 / record.plan.frequency_hz

    samples: list[TelemetrySampleResponse] = []
    for _ in range(count):
        samples.append(telemetry_sample_response(record.runner.tick(step), validator))
        if record.runner.is_completed:
            break

    return samples


def _get_record_or_404(
    registry: InMemorySyntheticMissionRegistry,
    mission_id: str,
) -> SyntheticMissionRecord:
    record = registry.get(mission_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Synthetic mission {mission_id!r} was not found.",
        )
    return record
