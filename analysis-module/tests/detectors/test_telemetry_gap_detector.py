from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import AnomalyType, Severity  # noqa: E402
from analysis_module.detectors.rule_based.rules import TelemetryGapRule  # noqa: E402
from analysis_module.features import TelemetryHistory  # noqa: E402


class TelemetryGapDetectorTest(unittest.TestCase):
    def test_expected_interval_does_not_report_anomaly(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = TelemetryGapRule(max_elapsed_sec=10.0).evaluate(
            telemetry(timestamp=seconds_after(5)),
            history,
        )

        self.assertIsNone(anomaly)

    def test_large_interval_reports_telemetry_gap(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = TelemetryGapRule(max_elapsed_sec=10.0).evaluate(
            telemetry(timestamp=seconds_after(20)),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.TELEMETRY_GAP)
        self.assertEqual(anomaly.severity, Severity.WARNING)
        self.assertEqual(anomaly.affected_fields, ("timestamp",))
        self.assertEqual(anomaly.evidence["gap_ms"], 20_000)
        self.assertEqual(anomaly.evidence["threshold_ms"], 10_000)


if __name__ == "__main__":
    unittest.main()
