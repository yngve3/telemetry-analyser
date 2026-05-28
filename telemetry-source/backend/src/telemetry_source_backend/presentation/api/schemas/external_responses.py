"""External source API response schemas."""

from pydantic import BaseModel


class ExternalSourceStatusResponse(BaseModel):
    source_id: str
    name: str
    address: str
    port: int
    protocol: str
    is_active: bool
    received_packets: int
    received_bytes: int
    last_received_at: str | None = None
    last_remote_address: str | None = None
    last_remote_port: int | None = None
    last_payload_size: int | None = None


class ExternalSourceCreatedResponse(BaseModel):
    source_id: str
    status: ExternalSourceStatusResponse


class ExternalSourceListItemResponse(BaseModel):
    source_id: str
    name: str
    address: str
    port: int
    protocol: str
    is_active: bool
    received_packets: int
