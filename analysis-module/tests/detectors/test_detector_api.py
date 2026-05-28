from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import seconds_after, telemetry

from analysis_module import (  # noqa: E402
    AnalysisContext,
    AnalyzerConfig,
    AnomalyType,
    DetectorConfigurationError,
    DetectorKind,
    create_detectors,
    create_ml_detector,
    create_neural_network_detector,
    create_rule_based_detector,
)
from analysis_module.features import TelemetryFeatureExtractor, TelemetryHistory  # noqa: E402


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

    def test_ml_and_nn_factories_reject_missing_artifacts(self) -> None:
        with self.assertRaises(DetectorConfigurationError):
            create_ml_detector(AnalyzerConfig(model_window_size=2))

        with self.assertRaises(DetectorConfigurationError):
            create_neural_network_detector(AnalyzerConfig(model_window_size=2))

    def test_create_detectors_uses_enabled_detector_names(self) -> None:
        detectors = create_detectors(
            AnalyzerConfig(enabled_detectors=("rule_based",))
        )

        self.assertEqual(
            [detector.name for detector in detectors],
            ["rule_based"],
        )

    def test_create_detectors_accepts_nn_autoencoder_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = _create_artifact(Path(directory))

            detectors = create_detectors(
                AnalyzerConfig(
                    enabled_detectors=("nn_autoencoder",),
                    nn_model_artifact_path=artifact_path,
                )
            )

        self.assertEqual([detector.name for detector in detectors], ["nn_autoencoder"])

    def test_create_detectors_accepts_nn_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = _create_artifact(Path(directory))

            detectors = create_detectors(
                AnalyzerConfig(
                    enabled_detectors=("nn",),
                    nn_model_artifact_path=artifact_path,
                )
            )

        self.assertEqual([detector.name for detector in detectors], ["nn_autoencoder"])

    def test_create_detectors_rejects_unknown_detector_name(self) -> None:
        with self.assertRaises(DetectorConfigurationError):
            create_detectors(AnalyzerConfig(enabled_detectors=("unknown",)))


def _create_artifact(path: Path) -> Path:
    feature_names = TelemetryFeatureExtractor().feature_names
    (path / "model.pt").write_bytes(b"")
    _write_json(
        path / "metadata.json",
        {
            "model_type": "autoencoder",
            "feature_version": "1.0",
            "window_size": 50,
            "feature_names": list(feature_names),
            "created_at": "2026-05-24T00:00:00Z",
        },
    )
    _write_json(path / "normalizer.json", {"type": "identity"})
    _write_json(path / "threshold.json", {"threshold": 0.75})
    return path


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
