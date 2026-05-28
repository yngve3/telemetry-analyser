"""External telemetry source adapter."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from telemetry_source_backend.domain.external.models import (
    ExternalSourceConfig,
    ExternalTelemetryPacket,
)

PacketHandler = Callable[[ExternalTelemetryPacket], None]


@dataclass(frozen=True, slots=True)
class ExternalUdpTelemetrySource:
    """Adapter that receives raw telemetry packets through UDP."""

    config: ExternalSourceConfig
    buffer_size: int = 4096

    async def receive_loop(
        self,
        stop_event: asyncio.Event,
        on_packet: PacketHandler,
    ) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.config.address, self.config.port))
            sock.settimeout(0.2)

            while not stop_event.is_set():
                try:
                    payload, remote = await asyncio.to_thread(
                        sock.recvfrom,
                        self.buffer_size,
                    )
                except socket.timeout:
                    continue

                on_packet(
                    ExternalTelemetryPacket(
                        received_at=datetime.now(tz=UTC),
                        payload=payload,
                        remote_address=remote[0],
                        remote_port=remote[1],
                    )
                )
        finally:
            sock.close()
