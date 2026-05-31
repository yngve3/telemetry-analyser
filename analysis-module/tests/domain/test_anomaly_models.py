from __future__ import annotations

import unittest

from support import telemetry

from analysis_module import (  # noqa: E402
    AnomalySource,
    AnomalyResult,
    AnomalyType,
    DetectedAnomaly,
    DetectorKind,
    DetectorOutput,
    Severity,
)


class AnomalyModelsTest(unittest.TestCase):
    def test_detected_anomaly_contains_detector_context(self) -> None:
        anomaly = DetectedAnomaly(
            type=AnomalyType.GPS_SPOOFING,
            severity=Severity.WARNING,
            message="GPS jump.",
            confidence=0.86,
            source="rule_based",
            detector_kind="rule_based",
            detector_name="GpsSpoofingRule",
            affected_fields=("latitude_deg", "longitude_deg"),
            evidence={"distance_delta_m": 130.4},
            probable_cause="Reported speed does not explain the position jump.",
        )

        self.assertEqual(anomaly.confidence, 0.86)
        self.assertEqual(anomaly.source, "rule_based")
        self.assertEqual(anomaly.detector_kind, "rule_based")
        self.assertEqual(anomaly.detector_name, "GpsSpoofingRule")
        self.assertEqual(anomaly.affected_fields, ("latitude_deg", "longitude_deg"))
        self.assertEqual(
            anomaly.affected_parameters,
            ("latitude_deg", "longitude_deg"),
        )
        self.assertEqual(anomaly.evidence["distance_delta_m"], 130.4)
        self.assertEqual(
            anomaly.probable_cause,
            "Reported speed does not explain the position jump.",
        )

    def test_result_reports_anomaly_presence_and_detector_outputs(self) -> None:
        sample = telemetry()
        source = AnomalySource(
            detector="rule_based",
            confidence=0.8,
            evidence={"battery_percent": 20.0},
            severity=Severity.WARNING,
        )
        anomaly = DetectedAnomaly(
            type=AnomalyType.LOW_BATTERY,
            severity=Severity.WARNING,
            message="Battery low.",
            confidence=0.8,
            detector_name="aggregated",
            sources=(source,),
        )
        result = AnomalyResult(
            drone_id=sample.drone_id,
            telemetry_timestamp=sample.timestamp,
            anomalies=(anomaly,),
            detector_outputs=(
                DetectorOutput(
                    detector_name="rule_based",
                    detector_kind=DetectorKind.RULE_BASED,
                    anomalies=(anomaly,),
                ),
            ),
        )

        self.assertTrue(result.has_anomalies)
        self.assertEqual(result.detector_outputs[0].detector_name, "rule_based")
        self.assertEqual(result.anomalies[0].sources[0].detector, "rule_based")

    def test_result_serializes_to_schema_shaped_dict(self) -> None:
        sample = telemetry()
        anomaly = DetectedAnomaly(
            type=AnomalyType.LOW_BATTERY,
            severity=Severity.WARNING,
            message="Battery low.",
            confidence=0.8,
            detector_name="aggregated",
            sources=(
                AnomalySource(
                    detector="rule_based",
                    confidence=0.8,
                    evidence={"battery_percent": 20.0},
                    severity=Severity.WARNING,
                ),
            ),
        )
        result = AnomalyResult(
            drone_id=sample.drone_id,
            telemetry_timestamp=sample.timestamp,
            anomalies=(anomaly,),
            detector_outputs=(
                DetectorOutput(
                    detector_name="rule_based",
                    detector_kind=DetectorKind.RULE_BASED,
                    anomalies=(
                        DetectedAnomaly(
                            type=AnomalyType.LOW_BATTERY,
                            severity=Severity.WARNING,
                            message="Battery low.",
                            confidence=0.8,
                            detector_name="LowBatteryRule",
                            evidence={"battery_percent": 20.0},
                        ),
                    ),
                ),
            ),
        )

        payload = result.to_dict()

        self.assertEqual(payload["has_anomalies"], True)
        self.assertIn("rule_based", payload["detector_outputs"])
        self.assertEqual(payload["anomalies"][0]["source"], "rule_based")
        self.assertEqual(payload["anomalies"][0]["detector_kind"], "rule_based")
        self.assertIn("affected_fields", payload["anomalies"][0])
        self.assertIn("affected_parameters", payload["anomalies"][0])
        self.assertEqual(
            payload["anomalies"][0]["sources"][0]["detector"],
            "rule_based",
        )


if __name__ == "__main__":
    unittest.main()
