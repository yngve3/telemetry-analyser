"""Application service for telemetry format conversion."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from telemetry_converter.application.ports import (
    TelemetryInputDecoder,
    TelemetryOutputEncoder,
)
from telemetry_converter.domain.models import UnifiedTelemetryPayload


class ConversionError(ValueError):
    """Raised when telemetry conversion cannot be completed."""


class TelemetryInputFormat(StrEnum):
    """Supported source payload formats."""

    MAVLINK_V2 = "mavlink.v2"


class TelemetryOutputFormat(StrEnum):
    """Supported target telemetry formats."""

    UNIFIED_TELEMETRY = "unified.telemetry"
    UNIFIED_TELEMETRY_DICT = "unified.telemetry.dict"


class UnifiedTelemetryEncoder:
    """Returns the unified telemetry DTO unchanged."""

    def encode(self, telemetry: UnifiedTelemetryPayload) -> UnifiedTelemetryPayload:
        return telemetry


class UnifiedTelemetryDictEncoder:
    """Returns a shared-contract compatible dictionary."""

    def encode(self, telemetry: UnifiedTelemetryPayload) -> dict[str, Any]:
        return telemetry.to_dict()


class TelemetryConverter:
    """Converts telemetry through registered input and output adapters."""

    def __init__(
        self,
        input_decoders: Mapping[TelemetryInputFormat, TelemetryInputDecoder],
        output_encoders: Mapping[TelemetryOutputFormat, TelemetryOutputEncoder],
    ) -> None:
        self._input_decoders = dict(input_decoders)
        self._output_encoders = dict(output_encoders)

    def convert(
        self,
        payload: bytes,
        source_format: TelemetryInputFormat = TelemetryInputFormat.MAVLINK_V2,
        target_format: TelemetryOutputFormat = TelemetryOutputFormat.UNIFIED_TELEMETRY,
    ) -> Any:
        decoder = self._input_decoders.get(source_format)
        if decoder is None:
            raise ConversionError(f"Unsupported telemetry source format: {source_format}.")

        output_encoder = self._output_encoders.get(target_format)
        if output_encoder is None:
            raise ConversionError(f"Unsupported telemetry target format: {target_format}.")

        try:
            telemetry = decoder.decode(payload)
        except ValueError as exc:
            raise ConversionError("Telemetry payload could not be decoded.") from exc

        return output_encoder.encode(telemetry)
