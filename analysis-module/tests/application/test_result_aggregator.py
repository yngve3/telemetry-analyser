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
        model_anomaly = DetectedAnomaly(
            type=AnomalyType.GPS_SPOOFING,
            severity=Severity.CRITICAL,
            message="Model confirmed GPS jump.",
            confidence=0.9,
            detector_name="isolation_forest",
            source="model_based",
            detector_kind="model_based",
            model_name="isolation_forest_baseline_v1",
            affected_parameters=("feature_window",),
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
                    detector_name="isolation_forest",
                    detector_kind=DetectorKind.MODEL_BASED,
                    anomalies=(model_anomaly,),
                ),
            ),
        )

        self.assertEqual(len(result.anomalies), 1)
        self.assertEqual(result.anomalies[0].type, AnomalyType.GPS_SPOOFING)
        self.assertEqual(result.anomalies[0].severity, Severity.CRITICAL)
        self.assertEqual(result.anomalies[0].confidence, 0.9)
        self.assertEqual(result.anomalies[0].source, "model_based")
        self.assertEqual(result.anomalies[0].detector_kind, "model_based")
        self.assertEqual(result.anomalies[0].detector_name, "isolation_forest")
        self.assertEqual(
            result.anomalies[0].model_name,
            "isolation_forest_baseline_v1",
        )
        self.assertEqual(result.anomalies[0].evidence["score"], 0.91)
        self.assertEqual(result.anomalies[0].probable_cause, "gps_spoofing")
        self.assertEqual(result.anomalies[0].cause_confidence, 0.9)
        self.assertTrue(result.anomalies[0].diagnostic_evidence)
        self.assertTrue(result.anomalies[0].recommended_action)
        self.assertEqual(
            [source.detector for source in result.anomalies[0].sources],
            ["rule_based", "isolation_forest"],
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
            detector_name="autoencoder",
            source="model_based",
        )

        result = ResultAggregator().aggregate_outputs(
            sample,
            (
                DetectorOutput(
                    detector_name="rule_based",
                    detector_kind=DetectorKind.RULE_BASED,
                ),
                DetectorOutput(
                    detector_name="autoencoder",
                    detector_kind=DetectorKind.MODEL_BASED,
                    anomalies=(anomaly,),
                ),
            ),
        )

        self.assertEqual(result.anomalies[0].type, AnomalyType.ANOMALOUS_BEHAVIOR)
        self.assertEqual(result.detector_outputs[1].anomalies, (anomaly,))

    def test_aggregator_sorts_anomalies_by_global_rank(self) -> None:
        sample = telemetry()
        low_battery = DetectedAnomaly(
            type=AnomalyType.LOW_BATTERY,
            severity=Severity.WARNING,
            message="Battery low.",
            confidence=0.95,
            detector_name="rule_based",
        )
        motion_rule = DetectedAnomaly(
            type=AnomalyType.MOTION_INCONSISTENCY,
            severity=Severity.CRITICAL,
            message="Motion mismatch.",
            confidence=0.8,
            detector_name="rule_based",
        )
        motion_model = DetectedAnomaly(
            type=AnomalyType.MOTION_INCONSISTENCY,
            severity=Severity.WARNING,
            message="Model motion mismatch.",
            confidence=0.75,
            detector_name="correlation_based",
            source="model_based",
        )

        result = ResultAggregator().aggregate_outputs(
            sample,
            (
                DetectorOutput(
                    detector_name="rule_based",
                    detector_kind=DetectorKind.RULE_BASED,
                    anomalies=(low_battery, motion_rule),
                ),
                DetectorOutput(
                    detector_name="correlation_based",
                    detector_kind=DetectorKind.MODEL_BASED,
                    anomalies=(motion_model,),
                ),
            ),
        )

        self.assertEqual(result.anomalies[0].type, AnomalyType.MOTION_INCONSISTENCY)
        self.assertEqual(result.anomalies[1].type, AnomalyType.LOW_BATTERY)
        self.assertEqual(
            [source.detector for source in result.anomalies[0].sources],
            ["rule_based", "correlation_based"],
        )


if __name__ == "__main__":
    unittest.main()
