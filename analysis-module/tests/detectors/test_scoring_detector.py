from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import AnomalyType  # noqa: E402
from analysis_module.detectors.model_based import ModelScore, ScoringDetector  # noqa: E402
from analysis_module.features import FeatureWindow, TelemetryHistory  # noqa: E402


class StaticScoringModel:
    def score(self, feature_window: FeatureWindow) -> ModelScore:
        return ModelScore(
            score=0.9,
            threshold=0.5,
            confidence=0.88,
            metadata={"model_type": "test"},
        )


class ScoringDetectorTest(unittest.TestCase):
    def test_scoring_detector_returns_anomaly_above_threshold(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = ScoringDetector(
            model=StaticScoringModel(),
            window_size=2,
        ).evaluate(
            telemetry(timestamp=seconds_after(1)),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.ANOMALOUS_BEHAVIOR)
        self.assertEqual(anomaly.confidence, 0.88)


if __name__ == "__main__":
    unittest.main()
