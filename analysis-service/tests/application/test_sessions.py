from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "analysis-service" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "analysis-module" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "telemetry-converter" / "src"))

from analysis_module import UnifiedTelemetry  # noqa: E402
from analysis_service.application import AnalysisProfile, SessionManager  # noqa: E402


class SessionManagerTest(unittest.TestCase):
    def test_session_keeps_analyzer_history_between_samples(self) -> None:
        manager = SessionManager()
        session = manager.create_session(
            session_id="history",
            profile=AnalysisProfile(enabled_rules=("battery_drop",)),
        )

        first_result = session.analyze(
            _telemetry(timestamp=_seconds_after(0), battery_percent=90.0)
        )
        second_result = session.analyze(
            _telemetry(timestamp=_seconds_after(2), battery_percent=80.0)
        )

        self.assertFalse(first_result.has_anomalies)
        self.assertTrue(second_result.has_anomalies)
        self.assertEqual(second_result.anomalies[0].type.value, "BATTERY_DROP")
        self.assertEqual(session.samples_analyzed, 2)

    def test_duplicate_session_id_is_rejected(self) -> None:
        manager = SessionManager()
        manager.create_session(session_id="uav-001")

        with self.assertRaises(ValueError):
            manager.create_session(session_id="uav-001")


def _seconds_after(seconds: int) -> datetime:
    return datetime(2026, 5, 24, 12, 0, tzinfo=UTC) + timedelta(seconds=seconds)


def _telemetry(
    timestamp: datetime = datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    battery_percent: float = 90.0,
) -> UnifiedTelemetry:
    return UnifiedTelemetry(
        timestamp=timestamp,
        drone_id="uav-001",
        latitude_deg=47.397742,
        longitude_deg=8.545594,
        altitude_m=30.0,
        battery_percent=battery_percent,
        satellites=10,
        ground_speed_m_s=8.0,
        heading_deg=90.0,
    )


if __name__ == "__main__":
    unittest.main()
