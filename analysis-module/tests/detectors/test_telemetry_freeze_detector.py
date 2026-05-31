from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import AnomalyType, Severity  # noqa: E402
from analysis_module.detectors.rule_based.rules import TelemetryFreezeRule  # noqa: E402
from analysis_module.features import TelemetryHistory  # noqa: E402


class TelemetryFreezeDetectorTest(unittest.TestCase):
    def test_changed_position_does_not_report_anomaly(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = TelemetryFreezeRule().evaluate(
            telemetry(timestamp=seconds_after(6), latitude_deg=55.7559),
            history,
        )

        self.assertIsNone(anomaly)

    def test_unchanged_values_report_telemetry_freeze(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = TelemetryFreezeRule().evaluate(
            telemetry(timestamp=seconds_after(6)),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.TELEMETRY_FREEZE)
        self.assertEqual(anomaly.severity, Severity.WARNING)
        self.assertIn("latitude_deg", anomaly.affected_fields)
        self.assertIn("elapsed_sec", anomaly.evidence)
        self.assertIn("distance_delta_m", anomaly.evidence)


if __name__ == "__main__":
    unittest.main()
