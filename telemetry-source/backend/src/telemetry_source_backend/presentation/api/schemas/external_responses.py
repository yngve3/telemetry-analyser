"""External source API response schemas."""

from pydantic import BaseModel


class ExternalSourceStatusResponse(BaseModel):
    source_id: str
    name: str
    address: str
    port: int
    protocol: str
    forward_enabled: bool
    forward_host: str
    forward_port: int
    is_active: bool
    received_packets: int
    received_bytes: int
    forwarded_packets: int
    last_received_at: str | None = None
    last_forwarded_at: str | None = None
    last_remote_address: str | None = None
    last_remote_port: int | None = None
    last_payload_size: int | None = None
    last_payload_preview_hex: str | None = None
    last_payload_preview_ascii: str | None = None
    last_payload_preview_truncated: bool = False
    last_error: str | None = None
    last_forward_error: str | None = None


class ExternalSourceCreatedResponse(BaseModel):
    source_id: str
    status: ExternalSourceStatusResponse


class ExternalSourceDeletedResponse(BaseModel):
    source_id: str
    deleted: bool


class ExternalSourceListItemResponse(BaseModel):
    source_id: str
    name: str
    address: str
    port: int
    protocol: str
    forward_enabled: bool
    forward_host: str
    forward_port: int
    is_active: bool
    received_packets: int
    forwarded_packets: int
