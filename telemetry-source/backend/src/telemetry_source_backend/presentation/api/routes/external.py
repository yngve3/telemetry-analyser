"""External source routes."""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from telemetry_source_backend.domain.exceptions import SourceConfigurationError
from telemetry_source_backend.domain.external.models import ExternalTelemetryPacket
from telemetry_source_backend.infrastructure.persistence.in_memory_external_source_registry import (
    ExternalSourceRecord,
)
from telemetry_source_backend.presentation.api.dependencies import (
    ExternalConnectionPolicyDep,
    ExternalSourceRecordDep,
    ExternalSourceRegistryDep,
    ExternalSourceRuntimeDependencies,
    ExternalSourceRuntimeDep,
)
from telemetry_source_backend.presentation.api.mappers.external import (
    external_config_from_request,
    external_source_list_item_response,
    external_source_status_response,
)
from telemetry_source_backend.presentation.api.schemas.external_requests import (
    ExternalSourceCreateRequest,
)
from telemetry_source_backend.presentation.api.schemas.external_responses import (
    ExternalSourceCreatedResponse,
    ExternalSourceDeletedResponse,
    ExternalSourceListItemResponse,
    ExternalSourceStatusResponse,
)

router = APIRouter(prefix="/sources/external", tags=["external"])


@router.post(
    "",
    response_model=ExternalSourceCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an external telemetry source",
)
async def create_external_source(
    request: ExternalSourceCreateRequest,
    registry: ExternalSourceRegistryDep,
    policy: ExternalConnectionPolicyDep,
) -> ExternalSourceCreatedResponse:
    try:
        config = external_config_from_request(request)
        policy.validate(config)
    except SourceConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    record = ExternalSourceRecord(config=config)
    registry.save(record)
    return ExternalSourceCreatedResponse(
        source_id=record.source_id,
        status=external_source_status_response(record),
    )


@router.get(
    "",
    response_model=list[ExternalSourceListItemResponse],
    summary="List external telemetry sources",
)
async def list_external_sources(
    registry: ExternalSourceRegistryDep,
) -> list[ExternalSourceListItemResponse]:
    return [
        external_source_list_item_response(record)
        for record in registry.list()
    ]


@router.get(
    "/{source_id}",
    response_model=ExternalSourceStatusResponse,
    summary="Get external source status",
)
async def get_external_source_status(
    record: ExternalSourceRecordDep,
) -> ExternalSourceStatusResponse:
    return external_source_status_response(_record_or_404(record))


@router.post(
    "/{source_id}/start",
    response_model=ExternalSourceStatusResponse,
    summary="Start external UDP telemetry ingestion",
)
async def start_external_source(
    record: ExternalSourceRecordDep,
    runtime: ExternalSourceRuntimeDep,
) -> ExternalSourceStatusResponse:
    source = _record_or_404(record)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"External source {source.source_id!r} was not found.",
        )

    if source.is_active:
        return external_source_status_response(source)

    source.stop_event.clear()
    source.last_error = None
    source.last_forward_error = None
    source.is_active = True
    source.task = asyncio.create_task(
        _run_external_receiver(source, runtime)
    )
    return external_source_status_response(source)


@router.post(
    "/{source_id}/stop",
    response_model=ExternalSourceStatusResponse,
    summary="Stop external UDP telemetry ingestion",
)
async def stop_external_source(
    record: ExternalSourceRecordDep,
) -> ExternalSourceStatusResponse:
    source = _record_or_404(record)
    await _stop_source_task(source)
    return external_source_status_response(source)


@router.delete(
    "/{source_id}",
    response_model=ExternalSourceDeletedResponse,
    summary="Delete external UDP telemetry source",
)
async def delete_external_source(
    source_id: str,
    registry: ExternalSourceRegistryDep,
) -> ExternalSourceDeletedResponse:
    source = registry.delete(source_id)
    _record_or_404(source)
    await _stop_source_task(source)
    return ExternalSourceDeletedResponse(source_id=source_id, deleted=True)


async def _run_external_receiver(
    record: ExternalSourceRecord,
    runtime: ExternalSourceRuntimeDependencies | None,
) -> None:
    if runtime is None:
        record.is_active = False
        return
    try:
        await runtime.receiver.receive_loop(
            record.stop_event,
            lambda packet: _handle_external_packet(record, runtime, packet),
        )
    except asyncio.CancelledError:
        raise
    except OSError as exc:
        record.last_error = str(exc)
    finally:
        record.is_active = False


async def _handle_external_packet(
    record: ExternalSourceRecord,
    runtime: ExternalSourceRuntimeDependencies,
    packet: ExternalTelemetryPacket,
) -> None:
    record.observe(packet)
    if runtime.forward_transport is None:
        return
    try:
        await runtime.forward_transport.send(packet.payload)
    except OSError as exc:
        record.observe_forward_error(str(exc))
        return
    record.observe_forward(datetime.now(tz=UTC))


async def _stop_source_task(source: ExternalSourceRecord) -> None:
    source.stop_event.set()
    if source.task is not None:
        source.task.cancel()
        try:
            await source.task
        except asyncio.CancelledError:
            pass
        source.task = None
    source.is_active = False


def _record_or_404(record: ExternalSourceRecord | None) -> ExternalSourceRecord:
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External source was not found.",
        )
    return record
