"""Telemetry mapping helpers between service payloads and analysis-module models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from datetime import datetime
from typing import Any

from analysis_module import UnifiedTelemetry
from telemetry_converter import UnifiedTelemetryPayload


def unified_telemetry_from_converter_payload(
    payload: UnifiedTelemetryPayload,
) -> UnifiedTelemetry:
    return UnifiedTelemetry(
        **{
            field.name: getattr(payload, field.name)
            for field in fields(UnifiedTelemetry)
        }
    )


def unified_telemetry_from_mapping(payload: Mapping[str, Any]) -> UnifiedTelemetry:
    values = dict(payload)
    timestamp = values.get("timestamp")
    if isinstance(timestamp, str):
        values["timestamp"] = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

    return UnifiedTelemetry(
        **{
            field.name: values[field.name]
            for field in fields(UnifiedTelemetry)
            if field.name in values
        }
    )


def unified_telemetry_to_dict(telemetry: UnifiedTelemetry) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in fields(UnifiedTelemetry):
        value = getattr(telemetry, field.name)
        if isinstance(value, datetime):
            payload[field.name] = value.isoformat()
        else:
            payload[field.name] = value
    return payload
