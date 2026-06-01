from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import ANALYSIS_MODULE_ROOT, seconds_after, telemetry

from analysis_module import (  # noqa: E402
    AnalyzerConfig,
    AnomalyType,
    DetectorConfigurationError,
    create_adaptive_correlation_based_detector,
    create_autoencoder_detector,
    create_analyzer,
    create_default_analyzer,
    create_isolation_forest_detector,
    create_rule_based_analyzer,
)
from analysis_module.features import SEQUENCE_FEATURE_NAMES  # noqa: E402


class AnalyzerFactoryTest(unittest.TestCase):
    def test_default_analyzer_uses_analyze_next_public_api(self) -> None:
        analyzer = create_default_analyzer()

        result = analyzer.analyze_next(telemetry())

        self.assertFalse(result.has_anomalies)
        self.assertEqual(result.detector_outputs[0].detector_name, "rule_based")
        self.assertIsNotNone(result.timing)
        self.assertIsNotNone(result.detector_outputs[0].duration_ms)
        self.assertIn("timing", result.to_dict())
        self.assertIn(
            "duration_ms",
            result.to_dict()["detector_outputs"]["rule_based"],
        )

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

    def test_pipeline_runs_rule_correlation_and_isolation_forest_outputs(self) -> None:
        analyzer = create_analyzer(
            AnalyzerConfig(
                enabled_detectors=(
                    "rule_based",
                    "correlation_based",
                    "isolation_forest",
                ),
                model_window_size=5,
            )
        )

        result = analyzer.analyze_next(telemetry(timestamp=seconds_after(0)))
        for index in range(1, 5):
            result = analyzer.analyze_next(
                telemetry(
                    timestamp=seconds_after(index),
                    latitude_deg=55.7558 + index * 0.00001,
                    longitude_deg=37.6173 + index * 0.00001,
                )
            )

        self.assertEqual(
            [output.detector_name for output in result.detector_outputs],
            ["rule_based", "correlation_based", "isolation_forest"],
        )
        self.assertIn(result.status, ("NORMAL", "WARNING", "CRITICAL"))
        self.assertIn(result.risk_level, ("NONE", "LOW", "MEDIUM", "HIGH"))

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
        self.assertEqual(result.detector_outputs[1].status.value, "not_ready")

    def test_autoencoder_detector_loads_configured_artifact(self) -> None:
        feature_names = SEQUENCE_FEATURE_NAMES
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

    def test_autoencoder_detector_loads_default_px4_artifact_when_runtime_is_available(
        self,
    ) -> None:
        try:
            import joblib  # noqa: F401
            import torch  # noqa: F401
        except ImportError:
            self.skipTest("joblib and PyTorch are not installed")

        detector = create_autoencoder_detector()

        self.assertIsNotNone(detector.scoring_model)
        self.assertEqual(detector.window_size, 20)

    def test_adaptive_correlation_detector_loads_configured_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile_path = Path(directory) / "adaptive_correlation_profile.json"
            _write_json(
                profile_path,
                {
                    "max_size": 10,
                    "min_samples": 2,
                    "percentile": 0.99,
                    "threshold_multiplier": 1.2,
                    "errors": {
                        "position_speed_error": [1.0, 2.0],
                        "altitude_velocity_error": [0.1, 0.2],
                        "heading_yaw_error": [4.0, 6.0],
                    },
                },
            )

            detector = create_adaptive_correlation_based_detector(
                AnalyzerConfig(adaptive_correlation_profile_path=profile_path)
            )

        self.assertEqual(detector.profile.count("position_speed_error"), 2)
        self.assertIsNotNone(
            detector.profile.adaptive_threshold("position_speed_error")
        )

    def test_isolation_forest_detector_loads_configured_artifact(self) -> None:
        try:
            import joblib  # noqa: F401
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("joblib and scikit-learn are not installed")

        artifact_path = ANALYSIS_MODULE_ROOT / "models" / "isolation_forest_px4"
        detector = create_isolation_forest_detector(
            AnalyzerConfig(isolation_forest_artifact_path=artifact_path)
        )

        self.assertIsNotNone(detector.artifact_model)
        self.assertEqual(detector.window_size, 20)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
