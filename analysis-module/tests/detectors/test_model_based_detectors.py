from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import (  # noqa: E402
    AnalysisContext,
    AnalyzerConfig,
    AnomalyType,
    DetectorPipelineAnalyzer,
    DetectorKind,
    create_rule_based_detector,
)
from analysis_module.detectors.model_based import (  # noqa: E402
    AdaptiveCorrelationBasedDetector,
    AdaptiveCorrelationProfile,
    IsolationForestArtifactModel,
    AutoencoderDetector,
    CorrelationBasedDetector,
    IsolationForestDetector,
)
from analysis_module.application.reason_diagnostics import FeatureStatistics  # noqa: E402
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

    def test_isolation_forest_artifact_adds_reason_diagnostics(self) -> None:
        history = TelemetryHistory()
        history.append(
            telemetry(
                timestamp=seconds_after(0),
                gps_eph=0.2,
                gps_epv=0.3,
            )
        )
        detector = IsolationForestDetector(
            window_size=2,
            min_window_size=2,
            artifact_model=IsolationForestArtifactModel(
                model=_FakeIsolationForestModel(),
                scaler=_IdentityScaler(),
                feature_names=("eph_mean", "epv_mean", "battery_warning_max"),
                threshold=0.0,
                window_size=2,
                feature_statistics={
                    "eph_mean": FeatureStatistics(mean=0.0, std=1.0),
                    "epv_mean": FeatureStatistics(mean=0.0, std=1.0),
                    "battery_warning_max": FeatureStatistics(mean=0.0, std=1.0),
                },
            ),
        )

        output = detector.analyze(
            AnalysisContext(
                current=telemetry(
                    timestamp=seconds_after(1),
                    gps_eph=20.0,
                    gps_epv=10.0,
                ),
                history=history,
            )
        )

        self.assertEqual(output.anomalies[0].detector_name, "isolation_forest")
        self.assertEqual(output.anomalies[0].reasons[0].group, "GPS")
        self.assertIn("reasons", output.anomalies[0].diagnostic_evidence)

    def test_autoencoder_detector_reports_not_ready_without_artifact(self) -> None:
        history = _normal_history()
        detector = AutoencoderDetector(
            window_size=8,
            min_window_size=5,
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
        self.assertEqual(output.status.value, "not_ready")
        self.assertEqual(output.anomalies, ())

    def test_adaptive_correlation_detector_uses_static_threshold_before_profile_ready(
        self,
    ) -> None:
        history = TelemetryHistory()
        history.append(_stationary_sample(0))
        detector = AdaptiveCorrelationBasedDetector(
            max_ground_speed_delta_m_s=5.0,
            profile=AdaptiveCorrelationProfile(min_samples=10),
        )

        output = detector.analyze(
            AnalysisContext(
                current=_stationary_sample(1, ground_speed_m_s=20.0),
                history=history,
            )
        )

        self.assertEqual(output.detector_kind, DetectorKind.MODEL_BASED)
        self.assertEqual(output.anomalies[0].type, AnomalyType.MOTION_INCONSISTENCY)
        self.assertEqual(output.anomalies[0].detector_name, "adaptive_correlation_based")
        self.assertEqual(
            output.anomalies[0].evidence["threshold_sources"][
                "position_speed_error"
            ],
            "static",
        )
        self.assertEqual(detector.profile.count("position_speed_error"), 0)

    def test_adaptive_profile_updates_after_clear_pipeline_result(self) -> None:
        detector = AdaptiveCorrelationBasedDetector(
            max_ground_speed_delta_m_s=5.0,
            max_vertical_speed_delta_m_s=5.0,
            profile=AdaptiveCorrelationProfile(max_size=10, min_samples=2),
        )
        analyzer = DetectorPipelineAnalyzer(
            detectors=(detector,),
            history=TelemetryHistory(),
        )

        analyzer.analyze_next(_stationary_sample(0))
        analyzer.analyze_next(_stationary_sample(1))
        analyzer.analyze_next(_stationary_sample(2))

        self.assertEqual(detector.profile.count("position_speed_error"), 2)
        payload = detector.profile.to_dict()
        restored_profile = AdaptiveCorrelationProfile.from_dict(payload)
        self.assertEqual(restored_profile.count("position_speed_error"), 2)
        self.assertEqual(
            restored_profile.adaptive_threshold("position_speed_error"),
            detector.profile.adaptive_threshold("position_speed_error"),
        )

        result = analyzer.analyze_next(
            _stationary_sample(3, ground_speed_m_s=20.0)
        )

        self.assertTrue(result.has_anomalies)
        self.assertEqual(detector.profile.count("position_speed_error"), 2)

    def test_adaptive_profile_skips_update_when_another_detector_confirms_anomaly(
        self,
    ) -> None:
        detector = AdaptiveCorrelationBasedDetector(
            max_ground_speed_delta_m_s=5.0,
            profile=AdaptiveCorrelationProfile(max_size=10, min_samples=2),
        )
        analyzer = DetectorPipelineAnalyzer(
            detectors=(
                detector,
                create_rule_based_detector(
                    AnalyzerConfig(enabled_rules=("low_battery",))
                ),
            ),
            history=TelemetryHistory(),
        )

        analyzer.analyze_next(_stationary_sample(0, battery_percent=90.0))
        result = analyzer.analyze_next(_stationary_sample(1, battery_percent=10.0))

        self.assertTrue(result.has_anomalies)
        self.assertEqual(detector.profile.count("position_speed_error"), 0)


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


def _stationary_sample(
    seconds: int,
    ground_speed_m_s: float = 0.0,
    battery_percent: float = 90.0,
):
    return telemetry(
        timestamp=seconds_after(seconds),
        latitude_deg=55.7558,
        longitude_deg=37.6173,
        altitude_m=120.0,
        battery_percent=battery_percent,
        ground_speed_m_s=ground_speed_m_s,
        vertical_speed_m_s=0.0,
        velocity_x_m_s=ground_speed_m_s,
        velocity_y_m_s=0.0,
        velocity_z_m_s=0.0,
        yaw_rad=0.0,
        message_quality=1.0,
    )


class _IdentityScaler:
    mean_ = [0.0, 0.0, 0.0]
    scale_ = [1.0, 1.0, 1.0]

    def transform(self, rows):
        return rows


class _FakeIsolationForestModel:
    def decision_function(self, rows):
        return [-1.0 for _ in rows]


if __name__ == "__main__":
    unittest.main()
