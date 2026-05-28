"""External source API request schemas."""

from pydantic import BaseModel, Field

from telemetry_source_backend.domain.external.models import ExternalTransportProtocol


class ExternalSourceCreateRequest(BaseModel):
    name: str
    address: str = "127.0.0.1"
    port: int = Field(ge=1, le=65535)
    protocol: ExternalTransportProtocol = ExternalTransportProtocol.UDP
