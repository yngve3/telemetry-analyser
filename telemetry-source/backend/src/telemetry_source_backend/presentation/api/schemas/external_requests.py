"""External source API request schemas."""

from pydantic import BaseModel, Field

from telemetry_source_backend.domain.external.models import ExternalTransportProtocol


class ExternalSourceCreateRequest(BaseModel):
    name: str
    address: str = "0.0.0.0"
    port: int = Field(default=14540, ge=1, le=65535)
    protocol: ExternalTransportProtocol = ExternalTransportProtocol.UDP
    forward_enabled: bool = True
    forward_host: str = "analysis-service"
    forward_port: int = Field(default=14560, ge=1, le=65535)
