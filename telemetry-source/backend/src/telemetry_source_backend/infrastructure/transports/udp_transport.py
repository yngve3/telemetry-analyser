"""UDP telemetry transport adapter."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class UdpTelemetryTransport:
    """Sends encoded telemetry through UDP."""

    host: str
    port: int

    async def send(self, payload: bytes) -> None:
        await asyncio.to_thread(self._send_sync, payload)

    def _send_sync(self, payload: bytes) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.sendto(payload, (self.host, self.port))
