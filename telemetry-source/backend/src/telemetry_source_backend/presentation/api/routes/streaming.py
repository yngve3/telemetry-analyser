"""Telemetry streaming routes."""

import asyncio

from fastapi import APIRouter, HTTPException, status

from telemetry_source_backend.application.ports import (
    TelemetryFrameEncoder,
    TelemetryTransport,
    TelemetryValidator,
)
from telemetry_source_backend.domain.snapshot.services import SnapshotCursor
from telemetry_source_backend.infrastructure.encoders.mavlink_encoder import (
    DEFAULT_MAVLINK_STREAM_RATE_PROFILE,
    MavlinkStreamRateScheduler,
    MavlinkTelemetryEncoder,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_synthetic_mission_registry import (
    InMemorySyntheticMissionRegistry,
    SyntheticMissionRecord,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_snapshot_registry import (
    InMemorySnapshotRegistry,
    SnapshotRecord,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_snapshot_stream_registry import (
    InMemorySnapshotStreamRegistry,
    SnapshotUdpStreamRecord,
)
from telemetry_source_backend.infrastructure.persistence.in_memory_synthetic_stream_registry import (
    InMemorySyntheticStreamRegistry,
    SyntheticUdpStreamRecord,
)
from telemetry_source_backend.presentation.api.dependencies import (
    SnapshotRegistryDep,
    SnapshotStreamRegistryDep,
    SyntheticMissionRegistryDep,
    SyntheticStreamRegistryDep,
    TelemetryValidatorDep,
    UdpPublicationDependencies,
    UdpPublicationDep,
)
from telemetry_source_backend.presentation.api.mappers.snapshot import (
    snapshot_udp_stream_status_response,
)
from telemetry_source_backend.presentation.api.mappers.synthetic import (
    telemetry_sample_response,
)
from telemetry_source_backend.presentation.api.schemas.snapshot_responses import (
    SnapshotUdpStreamStatusResponse,
)
from telemetry_source_backend.presentation.api.schemas.synthetic_responses import (
    StreamPreviewResponse,
    UdpStreamStatusResponse,
)

router = APIRouter(prefix="/streams", tags=["streams"])


@router.get("", summary="List telemetry stream capabilities")
async def list_stream_capabilities() -> dict[str, list[str]]:
    return {
        "available": [
            "Synthetic missions can publish MAVLink telemetry through UDP streams.",
            "Uploaded snapshots can be replayed as MAVLink telemetry through UDP streams.",
        ]
    }


@router.post(
    "/synthetic/missions/{mission_id}/udp",
    response_model=UdpStreamStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start continuous MAVLink-over-UDP publication",
)
async def start_synthetic_udp_stream(
    mission_id: str,
    publication: UdpPublicationDep,
    mission_registry: SyntheticMissionRegistryDep,
    stream_registry: SyntheticStreamRegistryDep,
) -> UdpStreamStatusResponse:
    request = publication.request
    mission = _get_mission_or_404(mission_registry, mission_id)
    frequency_hz = request.frequency_hz or mission.plan.frequency_hz
    record = SyntheticUdpStreamRecord(
        mission_id=mission_id,
        host=request.host,
        port=request.port,
        frequency_hz=frequency_hz,
    )
    record.is_active = True
    record.task = asyncio.create_task(
        _run_udp_stream(
            record,
            mission,
            publication.encoder,
            publication.transport,
            publication.validator,
        )
    )
    stream_registry.save(record)
    return _stream_status(record)


@router.get(
    "/udp",
    response_model=list[UdpStreamStatusResponse],
    summary="List UDP publication streams",
)
async def list_udp_streams(
    stream_registry: SyntheticStreamRegistryDep,
) -> list[UdpStreamStatusResponse]:
    return [_stream_status(record) for record in stream_registry.list()]


@router.get(
    "/udp/{stream_id}",
    response_model=UdpStreamStatusResponse,
    summary="Get UDP publication stream status",
)
async def get_udp_stream_status(
    stream_id: str,
    stream_registry: SyntheticStreamRegistryDep,
) -> UdpStreamStatusResponse:
    return _stream_status(_get_stream_or_404(stream_registry, stream_id))


@router.get(
    "/udp/{stream_id}/preview",
    response_model=StreamPreviewResponse,
    summary="Preview recent synthetic UDP stream samples",
)
async def get_udp_stream_preview(
    stream_id: str,
    stream_registry: SyntheticStreamRegistryDep,
    validator: TelemetryValidatorDep,
) -> StreamPreviewResponse:
    record = _get_stream_or_404(stream_registry, stream_id)
    return StreamPreviewResponse(
        stream_id=record.stream_id,
        samples=[
            telemetry_sample_response(sample, validator)
            for sample in record.preview_samples
        ],
    )


@router.delete(
    "/udp/{stream_id}",
    response_model=UdpStreamStatusResponse,
    summary="Stop UDP publication stream",
)
async def stop_udp_stream(
    stream_id: str,
    stream_registry: SyntheticStreamRegistryDep,
) -> UdpStreamStatusResponse:
    record = _get_stream_or_404(stream_registry, stream_id)
    record.stop_event.set()
    if record.task is not None:
        record.task.cancel()
        try:
            await record.task
        except asyncio.CancelledError:
            pass
    record.is_active = False
    return _stream_status(record)


@router.post(
    "/snapshots/{snapshot_id}/udp",
    response_model=SnapshotUdpStreamStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Replay a snapshot through MAVLink-over-UDP",
)
async def start_snapshot_udp_stream(
    snapshot_id: str,
    publication: UdpPublicationDep,
    snapshot_registry: SnapshotRegistryDep,
    stream_registry: SnapshotStreamRegistryDep,
) -> SnapshotUdpStreamStatusResponse:
    snapshot = _get_snapshot_or_404(snapshot_registry, snapshot_id)
    request = publication.request
    repeat = (
        request.repeat
        if request.repeat is not None
        else snapshot.snapshot.config.repeat
    )
    frequency_hz = request.frequency_hz or 1.0 / snapshot.snapshot.config.interval_seconds
    record = SnapshotUdpStreamRecord(
        snapshot_id=snapshot_id,
        host=request.host,
        port=request.port,
        frequency_hz=frequency_hz,
        repeat=repeat,
    )
    record.is_active = True
    record.task = asyncio.create_task(
        _run_snapshot_udp_stream(record, snapshot, publication)
    )
    stream_registry.save(record)
    return snapshot_udp_stream_status_response(record)


@router.get(
    "/snapshots/udp",
    response_model=list[SnapshotUdpStreamStatusResponse],
    summary="List snapshot UDP streams",
)
async def list_snapshot_udp_streams(
    stream_registry: SnapshotStreamRegistryDep,
) -> list[SnapshotUdpStreamStatusResponse]:
    return [
        snapshot_udp_stream_status_response(record)
        for record in stream_registry.list()
    ]


@router.get(
    "/snapshots/udp/{stream_id}",
    response_model=SnapshotUdpStreamStatusResponse,
    summary="Get snapshot UDP stream status",
)
async def get_snapshot_udp_stream_status(
    stream_id: str,
    stream_registry: SnapshotStreamRegistryDep,
) -> SnapshotUdpStreamStatusResponse:
    return snapshot_udp_stream_status_response(
        _get_snapshot_stream_or_404(stream_registry, stream_id)
    )


@router.get(
    "/snapshots/udp/{stream_id}/preview",
    response_model=StreamPreviewResponse,
    summary="Preview recent snapshot UDP stream samples",
)
async def get_snapshot_udp_stream_preview(
    stream_id: str,
    stream_registry: SnapshotStreamRegistryDep,
    validator: TelemetryValidatorDep,
) -> StreamPreviewResponse:
    record = _get_snapshot_stream_or_404(stream_registry, stream_id)
    return StreamPreviewResponse(
        stream_id=record.stream_id,
        samples=[
            telemetry_sample_response(sample, validator)
            for sample in record.preview_samples
        ],
    )


@router.delete(
    "/snapshots/udp/{stream_id}",
    response_model=SnapshotUdpStreamStatusResponse,
    summary="Stop snapshot UDP stream",
)
async def stop_snapshot_udp_stream(
    stream_id: str,
    stream_registry: SnapshotStreamRegistryDep,
) -> SnapshotUdpStreamStatusResponse:
    record = _get_snapshot_stream_or_404(stream_registry, stream_id)
    record.stop_event.set()
    if record.task is not None:
        record.task.cancel()
        try:
            await record.task
        except asyncio.CancelledError:
            pass
    record.is_active = False
    return snapshot_udp_stream_status_response(record)


async def _run_udp_stream(
    record: SyntheticUdpStreamRecord,
    mission: SyntheticMissionRecord,
    encoder: TelemetryFrameEncoder,
    transport: TelemetryTransport,
    validator: TelemetryValidator,
) -> None:
    if not mission.runner.state.is_running and not mission.runner.is_completed:
        mission.runner.resume()

    interval_sec = _stream_loop_interval_sec(record.frequency_hz)
    scheduler = MavlinkStreamRateScheduler()
    try:
        while not record.stop_event.is_set() and not mission.runner.is_completed:
            sample = mission.runner.tick(interval_sec)
            validator.validate_sample(sample)
            record.remember_sample(sample)
            message_ids = scheduler.due_message_ids(interval_sec)
            for frame in _encode_stream_messages(encoder, sample, message_ids):
                await transport.send(frame)
                record.sent_count += 1
            await asyncio.sleep(interval_sec)
    except asyncio.CancelledError:
        raise
    finally:
        record.is_active = False


async def _run_snapshot_udp_stream(
    record: SnapshotUdpStreamRecord,
    snapshot: SnapshotRecord,
    publication: UdpPublicationDependencies,
) -> None:
    sample_interval_sec = 1.0 / record.frequency_hz
    loop_interval_sec = _stream_loop_interval_sec(record.frequency_hz)
    scheduler = MavlinkStreamRateScheduler()
    cursor = SnapshotCursor(
        samples=snapshot.snapshot.samples,
        repeat=record.repeat,
    )
    current_sample = cursor.next()
    time_to_next_sample_sec = sample_interval_sec

    if current_sample is None:
        record.is_active = False
        return

    publication.validator.validate_sample(current_sample)
    record.remember_sample(current_sample)
    record.samples_sent += 1

    try:
        while not record.stop_event.is_set():
            message_ids = scheduler.due_message_ids(loop_interval_sec)
            for frame in _encode_stream_messages(
                publication.encoder,
                current_sample,
                message_ids,
            ):
                await publication.transport.send(frame)
                record.frames_sent += 1

            await asyncio.sleep(loop_interval_sec)
            time_to_next_sample_sec -= loop_interval_sec
            if time_to_next_sample_sec > 1e-9:
                continue

            next_sample = cursor.next()
            if next_sample is None:
                return

            current_sample = next_sample
            publication.validator.validate_sample(current_sample)
            record.remember_sample(current_sample)
            record.samples_sent += 1
            time_to_next_sample_sec += sample_interval_sec
    except asyncio.CancelledError:
        raise
    finally:
        record.is_active = False


def _stream_loop_interval_sec(requested_frequency_hz: float) -> float:
    loop_frequency_hz = max(
        requested_frequency_hz,
        DEFAULT_MAVLINK_STREAM_RATE_PROFILE.max_rate_hz,
    )
    return 1.0 / loop_frequency_hz


def _encode_stream_messages(
    encoder: TelemetryFrameEncoder,
    sample,
    message_ids: tuple[int, ...],
):
    if isinstance(encoder, MavlinkTelemetryEncoder):
        return encoder.encode_messages_for_ids(sample, message_ids)
    return encoder.encode_messages(sample)


def _get_mission_or_404(
    registry: InMemorySyntheticMissionRegistry,
    mission_id: str,
) -> SyntheticMissionRecord:
    mission = registry.get(mission_id)
    if mission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Synthetic mission {mission_id!r} was not found.",
        )
    return mission


def _get_stream_or_404(
    registry: InMemorySyntheticStreamRegistry,
    stream_id: str,
) -> SyntheticUdpStreamRecord:
    record = registry.get(stream_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UDP stream {stream_id!r} was not found.",
        )
    return record


def _get_snapshot_or_404(
    registry: InMemorySnapshotRegistry,
    snapshot_id: str,
) -> SnapshotRecord:
    record = registry.get(snapshot_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot {snapshot_id!r} was not found.",
        )
    return record


def _get_snapshot_stream_or_404(
    registry: InMemorySnapshotStreamRegistry,
    stream_id: str,
) -> SnapshotUdpStreamRecord:
    record = registry.get(stream_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot UDP stream {stream_id!r} was not found.",
        )
    return record


def _stream_status(record: SyntheticUdpStreamRecord) -> UdpStreamStatusResponse:
    return UdpStreamStatusResponse(
        stream_id=record.stream_id,
        mission_id=record.mission_id,
        host=record.host,
        port=record.port,
        frequency_hz=record.frequency_hz,
        is_active=record.is_active,
        sent_count=record.sent_count,
    )
