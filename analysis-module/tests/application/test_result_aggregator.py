from __future__ import annotations

import unittest

from support import telemetry

from analysis_module import AnomalyType, DetectedAnomaly, Severity  # noqa: E402
from analysis_module.domain import DetectorKind, DetectorOutput  # noqa: E402
from analysis_module.application import ResultAggregator  # noqa: E402


class ResultAggregatorTest(unittest.TestCase):
    def test_aggregator_groups_anomalies_by_type(self) -> None:
        sample = telemetry()
        rule_anomaly = DetectedAnomaly(
            type=AnomalyType.GPS_SPOOFING,
            severity=Severity.WARNING,
            message="GPS jump.",
            confidence=0.7,
            detector_name="rule_based",
            affected_fields=("latitude_deg", "longitude_deg"),
            evidence={"distance_delta_m": 130.4},
        )
        ml_anomaly = DetectedAnomaly(
            type=AnomalyType.GPS_SPOOFING,
            severity=Severity.CRITICAL,
            message="ML confirmed GPS jump.",
            confidence=0.9,
            detector_name="ml",
            source="ml",
            affected_fields=("feature_window",),
            evidence={"score": 0.91},
        )

        result = ResultAggregator().aggregate_outputs(
            sample,
            (
                DetectorOutput(
                    detector_name="rule_based",
                    detector_kind=DetectorKind.RULE_BASED,
                    anomalies=(rule_anomaly,),
                ),
                DetectorOutput(
                    detector_name="ml",
                    detector_kind=DetectorKind.ML,
                    anomalies=(ml_anomaly,),
                ),
            ),
        )

        self.assertEqual(len(result.anomalies), 1)
        self.assertEqual(result.anomalies[0].type, AnomalyType.GPS_SPOOFING)
        self.assertEqual(result.anomalies[0].severity, Severity.CRITICAL)
        self.assertEqual(result.anomalies[0].confidence, 0.9)
        self.assertEqual(result.anomalies[0].source, "ml")
        self.assertEqual(result.anomalies[0].detector_name, "ml")
        self.assertEqual(result.anomalies[0].evidence["score"], 0.91)
        self.assertEqual(
            [source.detector for source in result.anomalies[0].sources],
            ["rule_based", "ml"],
        )
        self.assertEqual(result.detector_outputs[0].detector_name, "rule_based")

    def test_legacy_aggregate_builds_sources_from_anomalies(self) -> None:
        sample = telemetry()
        anomalies = (
            DetectedAnomaly(
                type=AnomalyType.LOW_BATTERY,
                severity=Severity.WARNING,
                message="Battery low.",
                detector_name="LowBatteryRule",
            ),
        )

        result = ResultAggregator().aggregate(sample, anomalies)

        self.assertEqual(result.anomalies[0].type, AnomalyType.LOW_BATTERY)
        self.assertEqual(result.anomalies[0].sources[0].detector, "aggregated")
        self.assertEqual(result.drone_id, sample.drone_id)
        self.assertEqual(result.telemetry_timestamp, sample.timestamp)

    def test_aggregator_can_build_result_from_detector_outputs(self) -> None:
        sample = telemetry()
        anomaly = DetectedAnomaly(
            type=AnomalyType.ANOMALOUS_BEHAVIOR,
            severity=Severity.WARNING,
            message="Model score exceeded threshold.",
            confidence=0.7,
            detector_name="ml",
        )

        result = ResultAggregator().aggregate_outputs(
            sample,
            (
                DetectorOutput(
                    detector_name="rule_based",
                    detector_kind=DetectorKind.RULE_BASED,
                ),
                DetectorOutput(
                    detector_name="ml",
                    detector_kind=DetectorKind.ML,
                    anomalies=(anomaly,),
                ),
            ),
        )

        self.assertEqual(result.anomalies[0].type, AnomalyType.ANOMALOUS_BEHAVIOR)
        self.assertEqual(result.detector_outputs[1].anomalies, (anomaly,))


if __name__ == "__main__":
    unittest.main()
