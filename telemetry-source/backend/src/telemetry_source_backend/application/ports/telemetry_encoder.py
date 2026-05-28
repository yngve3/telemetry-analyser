"""Telemetry encoder port."""

from collections.abc import Sequence
from typing import Protocol

from telemetry_source_backend.domain.common.models import TelemetrySample


class TelemetryEncoder(Protocol):
    """Port for converting telemetry samples to external payloads."""

    def encode(self, sample: TelemetrySample) -> bytes:
        ...


class TelemetryFrameEncoder(Protocol):
    """Port for converting one telemetry sample to one or more frames."""

    def encode_messages(self, sample: TelemetrySample) -> Sequence[bytes]:
        ...
