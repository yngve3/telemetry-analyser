from __future__ import annotations

import unittest

from analysis_module import AnomalyType  # noqa: E402


class AnomalyTypesTest(unittest.TestCase):
    def test_anomaly_types_match_public_contract(self) -> None:
        self.assertEqual(
            {anomaly_type.value for anomaly_type in AnomalyType},
            {
                "GPS_SIGNAL_LOSS",
                "GPS_SPOOFING",
                "IMU_SPIKE",
                "MOTION_INCONSISTENCY",
                "BATTERY_DROP",
                "LOW_BATTERY",
                "TELEMETRY_FREEZE",
                "TELEMETRY_GAP",
                "IMPOSSIBLE_ALTITUDE",
                "ANOMALOUS_BEHAVIOR",
            },
        )


if __name__ == "__main__":
    unittest.main()
