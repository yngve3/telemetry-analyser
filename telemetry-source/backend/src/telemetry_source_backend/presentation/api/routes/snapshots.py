"""Snapshot source routes."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from telemetry_source_backend.infrastructure.persistence.in_memory_snapshot_registry import (
    InMemorySnapshotRegistry,
    SnapshotRecord,
)
from telemetry_source_backend.presentation.api.dependencies import (
    SnapshotRegistryDep,
    TelemetryValidatorDep,
    UdpPublicationDep,
)
from telemetry_source_backend.presentation.api.mappers.snapshot import (
    snapshot_from_request,
    snapshot_list_item_response,
    snapshot_status_response,
    telemetry_sample_response,
)
from telemetry_source_backend.presentation.api.schemas.snapshot_requests import (
    SnapshotCreateRequest,
)
from telemetry_source_backend.presentation.api.schemas.snapshot_responses import (
    SnapshotCreatedResponse,
    SnapshotListItemResponse,
    SnapshotSamplesResponse,
    SnapshotSendOnceResponse,
    SnapshotStatusResponse,
)

router = APIRouter(prefix="/sources/snapshots", tags=["snapshots"])


@router.post(
    "",
    response_model=SnapshotCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a telemetry snapshot",
)
async def create_snapshot(
    request: SnapshotCreateRequest,
    registry: SnapshotRegistryDep,
    validator: TelemetryValidatorDep,
) -> SnapshotCreatedResponse:
    snapshot_id = str(uuid4())
    try:
        snapshot = snapshot_from_request(snapshot_id, request, validator)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    record = SnapshotRecord(snapshot=snapshot, snapshot_id=snapshot_id)
    registry.save(record)
    return SnapshotCreatedResponse(
        snapshot_id=snapshot_id,
        status=snapshot_status_response(record),
    )


@router.get(
    "",
    response_model=list[SnapshotListItemResponse],
    summary="List uploaded snapshots",
)
async def list_snapshots(
    registry: SnapshotRegistryDep,
) -> list[SnapshotListItemResponse]:
    return [snapshot_list_item_response(record) for record in registry.list()]


@router.get(
    "/{snapshot_id}",
    response_model=SnapshotStatusResponse,
    summary="Get snapshot status",
)
async def get_snapshot_status(
    snapshot_id: str,
    registry: SnapshotRegistryDep,
) -> SnapshotStatusResponse:
    return snapshot_status_response(_get_snapshot_or_404(registry, snapshot_id))


@router.get(
    "/{snapshot_id}/samples",
    response_model=SnapshotSamplesResponse,
    summary="Read snapshot samples",
)
async def get_snapshot_samples(
    snapshot_id: str,
    registry: SnapshotRegistryDep,
    validator: TelemetryValidatorDep,
) -> SnapshotSamplesResponse:
    record = _get_snapshot_or_404(registry, snapshot_id)
    return SnapshotSamplesResponse(
        snapshot_id=snapshot_id,
        samples=[
            telemetry_sample_response(sample, validator)
            for sample in record.snapshot.samples
        ],
    )


@router.post(
    "/{snapshot_id}/send-once/udp",
    response_model=SnapshotSendOnceResponse,
    summary="Send a snapshot once through MAVLink-over-UDP",
)
async def send_snapshot_once_udp(
    snapshot_id: str,
    publication: UdpPublicationDep,
    registry: SnapshotRegistryDep,
) -> SnapshotSendOnceResponse:
    record = _get_snapshot_or_404(registry, snapshot_id)
    result = await publication.snapshot_publisher.send_once(record.snapshot.samples)
    return SnapshotSendOnceResponse(
        snapshot_id=snapshot_id,
        host=publication.request.host,
        port=publication.request.port,
        samples_sent=result.samples_sent,
        frames_sent=result.frames_sent,
    )


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
