"""Telemetry transport port."""

from typing import Protocol


class TelemetryTransport(Protocol):
    """Port for delivering encoded telemetry payloads."""

    async def send(self, payload: bytes) -> None:
        ...

