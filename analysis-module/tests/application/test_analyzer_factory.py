from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import seconds_after, telemetry

from analysis_module import (  # noqa: E402
    AnalyzerConfig,
    AnomalyType,
    DetectorConfigurationError,
    create_autoencoder_detector,
    create_analyzer,
    create_default_analyzer,
    create_rule_based_analyzer,
)
from analysis_module.features import TelemetryFeatureExtractor  # noqa: E402


class AnalyzerFactoryTest(unittest.TestCase):
    def test_default_analyzer_uses_analyze_next_public_api(self) -> None:
        analyzer = create_default_analyzer()

        result = analyzer.analyze_next(telemetry())

        self.assertFalse(result.has_anomalies)
        self.assertEqual(result.detector_outputs[0].detector_name, "rule_based")

    def test_rule_based_analyzer_keeps_history_for_stateful_rules(self) -> None:
        analyzer = create_rule_based_analyzer(
            AnalyzerConfig(enabled_rules=("battery_drop",))
        )
        analyzer.analyze_next(
            telemetry(timestamp=seconds_after(0), battery_percent=90.0)
        )

        result = analyzer.analyze_next(
            telemetry(timestamp=seconds_after(2), battery_percent=80.0)
        )

        self.assertEqual(result.anomalies[0].type, AnomalyType.BATTERY_DROP)

    def test_rule_thresholds_are_read_from_analyzer_config(self) -> None:
        analyzer = create_rule_based_analyzer(
            AnalyzerConfig(
                enabled_rules=("impossible_altitude",),
                thresholds={"impossible_altitude.max_altitude_m": 100.0},
            )
        )

        result = analyzer.analyze_next(telemetry(altitude_m=120.0))

        self.assertEqual(result.anomalies[0].type, AnomalyType.IMPOSSIBLE_ALTITUDE)

    def test_legacy_ml_detector_name_is_rejected(self) -> None:
        with self.assertRaises(DetectorConfigurationError):
            create_analyzer(
                AnalyzerConfig(
                    enabled_detectors=("ml",),
                    model_artifact_path=None,
                    model_window_size=2,
                )
            )

    def test_model_based_detectors_work_without_artifact(self) -> None:
        analyzer = create_analyzer(
            AnalyzerConfig(
                enabled_detectors=("correlation_based", "autoencoder"),
                model_window_size=5,
            )
        )

        result = analyzer.analyze_next(telemetry())

        self.assertEqual(
            [output.detector_name for output in result.detector_outputs],
            ["correlation_based", "autoencoder"],
        )

    def test_autoencoder_detector_loads_configured_artifact(self) -> None:
        feature_names = TelemetryFeatureExtractor().feature_names
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory)
            (artifact_path / "model.pt").write_bytes(b"")
            _write_json(
                artifact_path / "metadata.json",
                {
                    "model_type": "autoencoder",
                    "feature_version": "1.0",
                    "window_size": 50,
                    "feature_names": list(feature_names),
                    "created_at": "2026-05-24T00:00:00Z",
                },
            )
            _write_json(artifact_path / "normalizer.json", {"type": "identity"})
            _write_json(artifact_path / "threshold.json", {"threshold": 0.75})

            detector = create_autoencoder_detector(
                AnalyzerConfig(model_artifact_path=artifact_path)
            )

        self.assertIsNotNone(detector.scoring_model)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
