from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "telemetry-converter" / "src"))

from telemetry_converter import (  # noqa: E402
    TelemetryConverter,
    TelemetryInputFormat,
    TelemetryOutputFormat,
    UnifiedTelemetryPayload,
)


class StaticTelemetryDecoder:
    def decode(self, payload: bytes) -> UnifiedTelemetryPayload:
        return UnifiedTelemetryPayload(
            timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
            drone_id=payload.decode(),
            latitude_deg=47.397742,
            longitude_deg=8.545594,
            altitude_m=30.0,
            battery_percent=90.0,
            satellites=10,
        )


class DroneIdEncoder:
    def encode(self, telemetry: UnifiedTelemetryPayload) -> dict[str, Any]:
        return {"drone_id": telemetry.drone_id}


class TelemetryConverterDITest(unittest.TestCase):
    def test_converter_uses_injected_adapters(self) -> None:
        converter = TelemetryConverter(
            input_decoders={
                TelemetryInputFormat.MAVLINK_V2: StaticTelemetryDecoder(),
            },
            output_encoders={
                TelemetryOutputFormat.UNIFIED_TELEMETRY_DICT: DroneIdEncoder(),
            },
        )

        payload = converter.convert(
            b"uav-001",
            source_format=TelemetryInputFormat.MAVLINK_V2,
            target_format=TelemetryOutputFormat.UNIFIED_TELEMETRY_DICT,
        )

        self.assertEqual(payload, {"drone_id": "uav-001"})


if __name__ == "__main__":
    unittest.main()
