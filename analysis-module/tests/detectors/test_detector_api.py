from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import (  # noqa: E402
    AnalysisContext,
    AnalyzerConfig,
    AnomalyType,
    DetectorConfigurationError,
    DetectorKind,
    create_adaptive_correlation_based_detector,
    create_autoencoder_detector,
    create_correlation_based_detector,
    create_detectors,
    create_isolation_forest_detector,
    create_rule_based_detector,
)
from analysis_module.features import TelemetryHistory  # noqa: E402


class DetectorApiTest(unittest.TestCase):
    def test_rule_based_detector_reads_history_without_updating_it(self) -> None:
        history = TelemetryHistory()
        history.append(
            telemetry(timestamp=seconds_after(0), battery_percent=90.0)
        )
        detector = create_rule_based_detector(
            AnalyzerConfig(enabled_rules=("battery_drop",))
        )

        output = detector.analyze(
            AnalysisContext(
                current=telemetry(timestamp=seconds_after(2), battery_percent=80.0),
                history=history,
            )
        )

        self.assertEqual(output.detector_name, "rule_based")
        self.assertEqual(output.detector_kind, DetectorKind.RULE_BASED)
        self.assertEqual(output.anomalies[0].type, AnomalyType.BATTERY_DROP)
        self.assertEqual(len(history), 1)

    def test_create_detectors_uses_enabled_detector_names(self) -> None:
        detectors = create_detectors(
            AnalyzerConfig(
                enabled_detectors=(
                    "rule_based",
                    "correlation_based",
                    "adaptive_correlation_based",
                    "isolation_forest",
                    "autoencoder",
                ),
                model_window_size=8,
            )
        )

        self.assertEqual(
            [detector.name for detector in detectors],
            [
                "rule_based",
                "correlation_based",
                "adaptive_correlation_based",
                "isolation_forest",
                "autoencoder",
            ],
        )
        self.assertEqual(detectors[0].kind, DetectorKind.RULE_BASED)
        self.assertEqual(detectors[1].kind, DetectorKind.MODEL_BASED)
        self.assertEqual(detectors[2].kind, DetectorKind.MODEL_BASED)
        self.assertEqual(detectors[3].kind, DetectorKind.MODEL_BASED)
        self.assertEqual(detectors[4].kind, DetectorKind.MODEL_BASED)

    def test_create_detectors_accepts_model_detector_aliases(self) -> None:
        detectors = create_detectors(
            AnalyzerConfig(
                enabled_detectors=(
                    "correlation",
                    "adaptive_correlation",
                    "isolationforest",
                ),
                model_window_size=8,
            )
        )

        self.assertEqual(
            [detector.name for detector in detectors],
            [
                "correlation_based",
                "adaptive_correlation_based",
                "isolation_forest",
            ],
        )

    def test_model_detector_factories_use_model_based_kind(self) -> None:
        detectors = (
            create_correlation_based_detector(),
            create_adaptive_correlation_based_detector(),
            create_isolation_forest_detector(AnalyzerConfig(model_window_size=8)),
            create_autoencoder_detector(AnalyzerConfig(model_window_size=8)),
        )

        self.assertEqual(
            [detector.kind for detector in detectors],
            [DetectorKind.MODEL_BASED] * 4,
        )

    def test_create_detectors_rejects_legacy_ml_nn_names(self) -> None:
        for detector_name in ("ml", "nn", "nn_autoencoder"):
            with self.subTest(detector_name=detector_name):
                with self.assertRaises(DetectorConfigurationError):
                    create_detectors(
                        AnalyzerConfig(enabled_detectors=(detector_name,))
                    )

    def test_create_detectors_rejects_unknown_detector_name(self) -> None:
        with self.assertRaises(DetectorConfigurationError):
            create_detectors(AnalyzerConfig(enabled_detectors=("unknown",)))


if __name__ == "__main__":
    unittest.main()
