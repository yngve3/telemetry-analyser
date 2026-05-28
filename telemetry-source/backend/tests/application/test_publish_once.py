from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.application.use_cases.publish_once import PublishOnce  # noqa: E402
from telemetry_source_backend.domain.common.models import TelemetrySample  # noqa: E402


class MemorySource:
    async def read(self) -> TelemetrySample:
        return TelemetrySample(
            timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
            drone_id="uav-001",
            latitude_deg=55.7558,
            longitude_deg=37.6173,
            altitude_m=120.0,
            battery_percent=80.0,
            satellites=10,
        )


class MemoryEncoder:
    def encode(self, sample: TelemetrySample) -> bytes:
        return sample.drone_id.encode("utf-8")


class MemoryTransport:
    def __init__(self) -> None:
        self.payloads: list[bytes] = []

    async def send(self, payload: bytes) -> None:
        self.payloads.append(payload)


class PublishOnceTest(unittest.IsolatedAsyncioTestCase):
    async def test_publish_once_uses_source_encoder_and_transport(self) -> None:
        transport = MemoryTransport()
        use_case = PublishOnce(
            source=MemorySource(),
            encoder=MemoryEncoder(),
            transport=transport,
        )

        await use_case.execute()

        self.assertEqual(transport.payloads, [b"uav-001"])


if __name__ == "__main__":
    unittest.main()
