"""External raw telemetry packet model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ExternalTelemetryPacket:
    """Raw packet received from an external telemetry source."""

    received_at: datetime
    payload: bytes
    remote_address: str
    remote_port: int
