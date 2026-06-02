"""External source configuration."""

from dataclasses import dataclass

from telemetry_source_backend.domain.external.models.external_transport_protocol import (
    ExternalTransportProtocol,
)


@dataclass(frozen=True, slots=True)
class ExternalSourceConfig:
    """Configuration for connecting to an external telemetry source."""

    name: str
    address: str
    port: int
    protocol: ExternalTransportProtocol = ExternalTransportProtocol.UDP
    forward_enabled: bool = True
    forward_host: str = "analysis-service"
    forward_port: int = 14560
