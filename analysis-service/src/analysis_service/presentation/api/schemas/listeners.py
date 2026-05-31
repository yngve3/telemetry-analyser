"""Telemetry listener API schemas."""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field

from analysis_service.application import (
    ListenerConfig,
    ListenerPayloadFormat,
    ListenerProtocol,
    ListenerRecord,
)


class ListenerCreateRequest(BaseModel):
    session_id: str
    protocol: ListenerProtocol = ListenerProtocol.UDP
    format: ListenerPayloadFormat = ListenerPayloadFormat.MAVLINK_V2
    bind_host: str = "0.0.0.0"
    bind_port: int = Field(default=14560, ge=1, le=65535)
    buffer_size: int = Field(default=4096, gt=0)

    def to_config(self) -> ListenerConfig:
        return ListenerConfig(
            session_id=self.session_id,
            protocol=self.protocol,
            format=self.format,
            bind_host=self.bind_host,
            bind_port=self.bind_port,
            buffer_size=self.buffer_size,
        )


class ListenerResponse(BaseModel):
    listener_id: str
    session_id: str
    protocol: str
    format: str
    bind_host: str
    bind_port: int
    status: str
    received_packets: int
    received_bytes: int
    converted_samples: int
    analysis_errors: int
    created_at: str
    last_received_at: str | None = None
    last_remote_address: str | None = None
    last_remote_port: int | None = None
    last_telemetry_timestamp: str | None = None
    last_error: str | None = None
    last_result: dict[str, Any] | None = None

    @classmethod
    def from_record(cls, record: ListenerRecord) -> "ListenerResponse":
        return cls(**cast(Any, record.to_dict()))


class ListenerDeletedResponse(BaseModel):
    listener_id: str
    deleted: bool
