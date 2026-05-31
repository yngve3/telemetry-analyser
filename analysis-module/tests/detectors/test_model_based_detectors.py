from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import (  # noqa: E402
    AnalysisContext,
    AnomalyType,
    DetectorKind,
)
from analysis_module.detectors.model_based import (  # noqa: E402
    AutoencoderDetector,
    CorrelationBasedDetector,
    IsolationForestDetector,
)
from analysis_module.features import TelemetryHistory  # noqa: E402


class ModelBasedDetectorsTest(unittest.TestCase):
    def test_correlation_based_detector_detects_motion_inconsistency(self) -> None:
        history = TelemetryHistory()
        history.append(
            telemetry(
                timestamp=seconds_after(0),
                latitude_deg=55.7558,
                longitude_deg=37.6173,
                ground_speed_m_s=1.0,
                velocity_x_m_s=1.0,
                velocity_y_m_s=0.0,
            )
        )
        detector = CorrelationBasedDetector()

        output = detector.analyze(
            AnalysisContext(
                current=telemetry(
                    timestamp=seconds_after(1),
                    latitude_deg=55.7658,
                    longitude_deg=37.6173,
                    ground_speed_m_s=1.0,
                    velocity_x_m_s=1.0,
                    velocity_y_m_s=0.0,
                ),
                history=history,
            )
        )

        self.assertEqual(output.detector_kind, DetectorKind.MODEL_BASED)
        self.assertEqual(output.anomalies[0].type, AnomalyType.MOTION_INCONSISTENCY)
        self.assertEqual(output.anomalies[0].detector_kind, "model_based")
        self.assertEqual(output.anomalies[0].model_name, "correlation_baseline_v1")
        self.assertIn("latitude_deg", output.anomalies[0].affected_parameters)
        self.assertIsNotNone(output.anomalies[0].window_start)
        self.assertIsNotNone(output.anomalies[0].window_end)

    def test_isolation_forest_detector_detects_feature_outlier(self) -> None:
        history = _normal_history()
        detector = IsolationForestDetector(
            window_size=8,
            min_window_size=5,
            n_trees=16,
            score_threshold=0.55,
        )

        output = detector.analyze(
            AnalysisContext(
                current=telemetry(
                    timestamp=seconds_after(8),
                    battery_percent=5.0,
                    battery_voltage_v=9.0,
                    altitude_m=450.0,
                ),
                history=history,
            )
        )

        self.assertEqual(output.detector_kind, DetectorKind.MODEL_BASED)
        self.assertEqual(output.anomalies[0].type, AnomalyType.ANOMALOUS_BEHAVIOR)
        self.assertEqual(output.anomalies[0].detector_name, "isolation_forest")
        self.assertEqual(
            output.anomalies[0].model_name,
            "isolation_forest_baseline_v1",
        )
        self.assertIn("score", output.anomalies[0].evidence)
        self.assertTrue(output.anomalies[0].affected_parameters)

    def test_autoencoder_detector_detects_reconstruction_error(self) -> None:
        history = _normal_history()
        detector = AutoencoderDetector(
            window_size=8,
            min_window_size=5,
            reconstruction_error_threshold=1.0,
        )

        output = detector.analyze(
            AnalysisContext(
                current=telemetry(
                    timestamp=seconds_after(8),
                    battery_percent=5.0,
                    battery_voltage_v=9.0,
                    altitude_m=450.0,
                ),
                history=history,
            )
        )

        self.assertEqual(output.detector_kind, DetectorKind.MODEL_BASED)
        self.assertEqual(output.anomalies[0].type, AnomalyType.ANOMALOUS_BEHAVIOR)
        self.assertEqual(output.anomalies[0].detector_name, "autoencoder")
        self.assertEqual(
            output.anomalies[0].model_name,
            "autoencoder_reconstruction_baseline_v1",
        )
        self.assertIn("reconstruction_error", output.anomalies[0].evidence)
        self.assertTrue(output.anomalies[0].probable_cause)


def _normal_history() -> TelemetryHistory:
    history = TelemetryHistory()
    for index in range(8):
        history.append(
            telemetry(
                timestamp=seconds_after(index),
                latitude_deg=55.7558 + index * 0.00001,
                longitude_deg=37.6173 + index * 0.00001,
                altitude_m=120.0 + index * 0.2,
                battery_percent=80.0 - index * 0.2,
                battery_voltage_v=12.2 - index * 0.01,
                ground_speed_m_s=2.0 + index * 0.05,
                vertical_speed_m_s=0.2,
                velocity_x_m_s=2.0 + index * 0.05,
                velocity_y_m_s=0.0,
            )
        )
    return history


if __name__ == "__main__":
    unittest.main()
