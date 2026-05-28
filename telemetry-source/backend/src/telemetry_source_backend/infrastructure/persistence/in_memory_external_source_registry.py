"""In-memory registry for external telemetry sources."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from telemetry_source_backend.domain.external.models import (
    ExternalSourceConfig,
    ExternalTelemetryPacket,
)


@dataclass(slots=True)
class ExternalSourceRecord:
    """Runtime state for an external source connection."""

    config: ExternalSourceConfig
    source_id: str = field(default_factory=lambda: str(uuid4()))
    is_active: bool = False
    received_packets: int = 0
    received_bytes: int = 0
    last_received_at: datetime | None = None
    last_remote_address: str | None = None
    last_remote_port: int | None = None
    last_payload_size: int | None = None
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task[None] | None = None

    def observe(self, packet: ExternalTelemetryPacket) -> None:
        self.received_packets += 1
        self.received_bytes += len(packet.payload)
        self.last_received_at = packet.received_at
        self.last_remote_address = packet.remote_address
        self.last_remote_port = packet.remote_port
        self.last_payload_size = len(packet.payload)


class InMemoryExternalSourceRegistry:
    """Stores external source runtime records for the backend process lifetime."""

    def __init__(self) -> None:
        self._records: dict[str, ExternalSourceRecord] = {}

    def save(self, record: ExternalSourceRecord) -> None:
        self._records[record.source_id] = record

    def get(self, source_id: str) -> ExternalSourceRecord | None:
        return self._records.get(source_id)

    def list(self) -> list[ExternalSourceRecord]:
        return list(self._records.values())
