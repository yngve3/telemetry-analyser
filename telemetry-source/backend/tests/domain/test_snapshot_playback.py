from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.domain.common.models import TelemetrySample  # noqa: E402
from telemetry_source_backend.domain.snapshot.services import SnapshotCursor  # noqa: E402


class SnapshotPlaybackTest(unittest.TestCase):
    def test_cursor_stops_after_last_sample_without_repeat(self) -> None:
        cursor = SnapshotCursor(samples=(self._sample("a"), self._sample("b")))

        self.assertEqual(cursor.next().drone_id, "a")
        self.assertEqual(cursor.next().drone_id, "b")
        self.assertIsNone(cursor.next())

    def test_cursor_repeats_when_enabled(self) -> None:
        cursor = SnapshotCursor(samples=(self._sample("a"),), repeat=True)

        self.assertEqual(cursor.next().drone_id, "a")
        self.assertEqual(cursor.next().drone_id, "a")

    def _sample(self, drone_id: str) -> TelemetrySample:
        return TelemetrySample(
            timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
            drone_id=drone_id,
            latitude_deg=47.397742,
            longitude_deg=8.545594,
            altitude_m=30.0,
            battery_percent=90.0,
            satellites=10,
        )


if __name__ == "__main__":
    unittest.main()
