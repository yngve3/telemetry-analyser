from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import (  # noqa: E402
    AnalyzerConfig,
    AnomalyType,
    DetectorConfigurationError,
    create_analyzer,
    create_default_analyzer,
    create_rule_based_analyzer,
)


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

    def test_enabled_model_detector_without_artifact_is_rejected(self) -> None:
        with self.assertRaises(DetectorConfigurationError):
            create_analyzer(
                AnalyzerConfig(
                    enabled_detectors=("rule_based",),
                    enable_model_detector=True,
                    model_artifact_path=None,
                    model_window_size=2,
                )
            )


if __name__ == "__main__":
    unittest.main()
