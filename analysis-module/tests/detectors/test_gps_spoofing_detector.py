from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import AnomalyType, Severity  # noqa: E402
from analysis_module.detectors.rule_based.rules import GpsSpoofingRule  # noqa: E402
from analysis_module.features import TelemetryHistory  # noqa: E402


class GpsSpoofingDetectorTest(unittest.TestCase):
    def test_normal_position_delta_does_not_report_anomaly(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = GpsSpoofingRule().evaluate(
            telemetry(timestamp=seconds_after(1), latitude_deg=55.75581),
            history,
        )

        self.assertIsNone(anomaly)

    def test_large_position_jump_reports_gps_spoofing(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = GpsSpoofingRule().evaluate(
            telemetry(
                timestamp=seconds_after(1),
                latitude_deg=55.7758,
                ground_speed_m_s=8.0,
            ),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.GPS_SPOOFING)
        self.assertEqual(anomaly.severity, Severity.CRITICAL)
        self.assertIn("latitude_deg", anomaly.affected_fields)
        self.assertIn("distance_delta_m", anomaly.evidence)
        self.assertIn("calculated_speed_m_s", anomaly.evidence)
        self.assertIn("threshold_m_s", anomaly.evidence)


if __name__ == "__main__":
    unittest.main()
