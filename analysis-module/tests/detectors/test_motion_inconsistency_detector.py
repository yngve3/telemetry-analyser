from __future__ import annotations

import unittest

from support import telemetry

from analysis_module import AnomalyType, Severity  # noqa: E402
from analysis_module.detectors.rule_based.rules import (  # noqa: E402
    MotionInconsistencyRule,
)
from analysis_module.features import TelemetryHistory  # noqa: E402


class MotionInconsistencyDetectorTest(unittest.TestCase):
    def test_consistent_velocity_vector_does_not_report_anomaly(self) -> None:
        anomaly = MotionInconsistencyRule().evaluate(
            telemetry(
                ground_speed_m_s=12.5,
                velocity_x_m_s=12.5,
                velocity_y_m_s=0.0,
            ),
            TelemetryHistory(),
        )

        self.assertIsNone(anomaly)

    def test_inconsistent_velocity_vector_reports_motion_inconsistency(self) -> None:
        anomaly = MotionInconsistencyRule().evaluate(
            telemetry(
                ground_speed_m_s=5.0,
                velocity_x_m_s=25.0,
                velocity_y_m_s=0.0,
            ),
            TelemetryHistory(),
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.MOTION_INCONSISTENCY)
        self.assertEqual(anomaly.severity, Severity.CRITICAL)
        self.assertIn("velocity_x_m_s", anomaly.affected_fields)
        self.assertIn("speed_delta_m_s", anomaly.evidence)
        self.assertEqual(anomaly.evidence["reference_source"], "velocity_vector")


if __name__ == "__main__":
    unittest.main()
