"""Telemetry converter module."""

from typing import Any

from telemetry_converter.application.converter import (
    ConversionError,
    TelemetryConverter,
    TelemetryInputFormat,
    TelemetryOutputFormat,
    UnifiedTelemetryDictEncoder as _UnifiedTelemetryDictEncoder,
    UnifiedTelemetryEncoder as _UnifiedTelemetryEncoder,
)
from telemetry_converter.application.ports import (
    TelemetryInputDecoder,
    TelemetryOutputEncoder,
    TelemetryStreamDecoder,
)
from telemetry_converter.domain.models import UnifiedTelemetryPayload


def default_converter() -> TelemetryConverter:
    from telemetry_converter.infrastructure.mavlink_decoder import MavlinkV2TelemetryDecoder

    return TelemetryConverter(
        input_decoders={
            TelemetryInputFormat.MAVLINK_V2: MavlinkV2TelemetryDecoder(),
        },
        output_encoders={
            TelemetryOutputFormat.UNIFIED_TELEMETRY: _UnifiedTelemetryEncoder(),
            TelemetryOutputFormat.UNIFIED_TELEMETRY_DICT: _UnifiedTelemetryDictEncoder(),
        },
    )


def default_mavlink_stream_decoder() -> TelemetryStreamDecoder:
    from telemetry_converter.infrastructure.mavlink_decoder import (
        MavlinkV2TelemetryStreamDecoder,
    )

    return MavlinkV2TelemetryStreamDecoder()


def convert(
    payload: bytes,
    source_format: TelemetryInputFormat = TelemetryInputFormat.MAVLINK_V2,
    target_format: TelemetryOutputFormat = TelemetryOutputFormat.UNIFIED_TELEMETRY,
) -> Any:
    return default_converter().convert(
        payload=payload,
        source_format=source_format,
        target_format=target_format,
    )


__all__ = [
    "ConversionError",
    "TelemetryConverter",
    "TelemetryInputDecoder",
    "TelemetryInputFormat",
    "TelemetryOutputEncoder",
    "TelemetryOutputFormat",
    "TelemetryStreamDecoder",
    "UnifiedTelemetryPayload",
    "convert",
    "default_converter",
    "default_mavlink_stream_decoder",
]
