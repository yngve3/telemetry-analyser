from __future__ import annotations

import unittest

from support import telemetry

from analysis_module import AnomalyType, Severity  # noqa: E402
from analysis_module.detectors.rule_based.rules import (  # noqa: E402
    ImpossibleAltitudeRule,
)
from analysis_module.features import TelemetryHistory  # noqa: E402


class ImpossibleAltitudeDetectorTest(unittest.TestCase):
    def test_expected_altitude_does_not_report_anomaly(self) -> None:
        anomaly = ImpossibleAltitudeRule().evaluate(
            telemetry(altitude_m=120.0),
            TelemetryHistory(),
        )

        self.assertIsNone(anomaly)

    def test_out_of_range_altitude_reports_impossible_altitude(self) -> None:
        anomaly = ImpossibleAltitudeRule().evaluate(
            telemetry(altitude_m=31_000.0),
            TelemetryHistory(),
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.IMPOSSIBLE_ALTITUDE)
        self.assertEqual(anomaly.severity, Severity.CRITICAL)
        self.assertEqual(anomaly.affected_fields, ("altitude_m",))
        self.assertEqual(anomaly.evidence["altitude_m"], 31_000.0)
        self.assertEqual(anomaly.evidence["max_altitude_m"], 30_000.0)


if __name__ == "__main__":
    unittest.main()
