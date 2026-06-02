"""Mappers for external source API schemas."""

from telemetry_source_backend.domain.external.models import ExternalSourceConfig
from telemetry_source_backend.infrastructure.persistence.in_memory_external_source_registry import (
    ExternalSourceRecord,
)
from telemetry_source_backend.presentation.api.schemas.external_requests import (
    ExternalSourceCreateRequest,
)
from telemetry_source_backend.presentation.api.schemas.external_responses import (
    ExternalSourceListItemResponse,
    ExternalSourceStatusResponse,
)


def external_config_from_request(
    request: ExternalSourceCreateRequest,
) -> ExternalSourceConfig:
    return ExternalSourceConfig(
        name=request.name,
        address=request.address,
        port=request.port,
        protocol=request.protocol,
        forward_enabled=request.forward_enabled,
        forward_host=request.forward_host,
        forward_port=request.forward_port,
    )


def external_source_status_response(
    record: ExternalSourceRecord,
) -> ExternalSourceStatusResponse:
    return ExternalSourceStatusResponse(
        source_id=record.source_id,
        name=record.config.name,
        address=record.config.address,
        port=record.config.port,
        protocol=record.config.protocol.value,
        forward_enabled=record.config.forward_enabled,
        forward_host=record.config.forward_host,
        forward_port=record.config.forward_port,
        is_active=record.is_active,
        received_packets=record.received_packets,
        received_bytes=record.received_bytes,
        forwarded_packets=record.forwarded_packets,
        last_received_at=(
            record.last_received_at.isoformat()
            if record.last_received_at is not None
            else None
        ),
        last_forwarded_at=(
            record.last_forwarded_at.isoformat()
            if record.last_forwarded_at is not None
            else None
        ),
        last_remote_address=record.last_remote_address,
        last_remote_port=record.last_remote_port,
        last_payload_size=record.last_payload_size,
        last_payload_preview_hex=record.last_payload_preview_hex,
        last_payload_preview_ascii=record.last_payload_preview_ascii,
        last_payload_preview_truncated=record.last_payload_preview_truncated,
        last_error=record.last_error,
        last_forward_error=record.last_forward_error,
    )


def external_source_list_item_response(
    record: ExternalSourceRecord,
) -> ExternalSourceListItemResponse:
    return ExternalSourceListItemResponse(
        source_id=record.source_id,
        name=record.config.name,
        address=record.config.address,
        port=record.config.port,
        protocol=record.config.protocol.value,
        forward_enabled=record.config.forward_enabled,
        forward_host=record.config.forward_host,
        forward_port=record.config.forward_port,
        is_active=record.is_active,
        received_packets=record.received_packets,
        forwarded_packets=record.forwarded_packets,
    )
