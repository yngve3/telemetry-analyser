from __future__ import annotations

import json
import unittest

from support import ANALYSIS_MODULE_ROOT, seconds_after, telemetry

from analysis_module.features import TelemetryFeatureExtractor  # noqa: E402
from analysis_module.features.model_features import (  # noqa: E402
    extract_sequence_diagnostic_values,
    extract_sequence_feature_values,
    extract_window_feature_values,
)


class TelemetryFeatureExtractorTest(unittest.TestCase):
    def test_feature_order_is_stable(self) -> None:
        extractor = TelemetryFeatureExtractor()

        self.assertEqual(
            extractor.feature_names,
            (
                "battery_percent",
                "battery_voltage_v",
                "satellites_visible",
                "gps_fix_type",
                "gps_eph",
                "gps_epv",
                "altitude_m",
                "ground_speed_m_s",
                "vertical_speed_m_s",
                "roll_rad",
                "pitch_rad",
                "yaw_rad",
                "roll_rate_rad_s",
                "pitch_rate_rad_s",
                "yaw_rate_rad_s",
                "delta_position_m",
                "delta_altitude_m",
                "delta_battery_percent",
                "delta_heading_deg",
                "elapsed_sec",
                "attitude_age_ms",
                "position_age_ms",
                "gps_age_ms",
                "system_age_ms",
                "message_quality",
            ),
        )

    def test_extracts_delta_features_from_previous_sample(self) -> None:
        extractor = TelemetryFeatureExtractor()
        previous = telemetry(
            timestamp=seconds_after(0),
            altitude_m=100.0,
            battery_percent=80.0,
            heading_deg=350.0,
        )
        current = telemetry(
            timestamp=seconds_after(2),
            latitude_deg=previous.latitude_deg + 0.001,
            altitude_m=110.0,
            battery_percent=78.0,
            heading_deg=10.0,
        )

        vector = extractor.extract(current, previous)
        values = vector.to_dict()

        self.assertGreater(values["delta_position_m"], 100.0)
        self.assertEqual(values["delta_altitude_m"], 10.0)
        self.assertEqual(values["delta_battery_percent"], -2.0)
        self.assertEqual(values["delta_heading_deg"], 20.0)
        self.assertEqual(values["elapsed_sec"], 2.0)
        self.assertEqual(values["message_quality"], 1.0)

    def test_window_features_follow_isolation_forest_metadata_order(self) -> None:
        feature_names = _metadata_feature_names("isolation_forest_px4")
        samples = _px4_samples(window_size=20)

        values = extract_window_feature_values(samples, feature_names)

        self.assertEqual(tuple(values), feature_names)
        self.assertTrue(all(value == value for value in values.values()))
        self.assertEqual(values["gps_check_fail_flags_max"], 1.0)
        self.assertEqual(values["battery_warning_max"], 2.0)
        self.assertEqual(values["fd_critical_failure_max"], 1.0)

    def test_sequence_features_follow_autoencoder_metadata_order(self) -> None:
        feature_names = _metadata_feature_names("autoencoder_px4")
        samples = _px4_samples(window_size=20)

        values = extract_sequence_feature_values(samples, feature_names)
        diagnostics = extract_sequence_diagnostic_values(samples, feature_names)

        self.assertEqual(len(values), len(samples) * len(feature_names))
        self.assertTrue(all(value == value for value in values))
        self.assertEqual(diagnostics["battery_remaining"], 0.8)
        self.assertEqual(diagnostics["battery_warning"], 2.0)
        self.assertEqual(diagnostics["fd_critical_failure"], 1.0)


def _metadata_feature_names(model_name: str) -> tuple[str, ...]:
    metadata_path = ANALYSIS_MODULE_ROOT / "models" / model_name / "metadata.json"
    with metadata_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)
    return tuple(metadata["feature_names"])


def _px4_samples(window_size: int):
    return tuple(
        telemetry(
            timestamp=seconds_after(index),
            latitude_deg=55.7558 + index * 0.00001,
            longitude_deg=37.6173 + index * 0.00001,
            altitude_m=120.0 + index * 0.1,
            battery_percent=80.0,
            battery_voltage_v=12.2,
            ground_speed_m_s=2.0,
            velocity_x_m_s=2.0,
            velocity_y_m_s=0.0,
            velocity_z_m_s=0.1,
            roll_rad=0.0,
            pitch_rad=0.0,
            yaw_rad=0.0,
            gps_fix_type=3,
            satellites_visible=10,
            gps_eph=0.5,
            gps_epv=0.8,
            gps_check_fail_flags=1 if index == window_size - 1 else 0,
            battery_warning=2 if index == window_size - 1 else 0,
            fd_critical_failure=1 if index == window_size - 1 else 0,
        )
        for index in range(window_size)
    )


if __name__ == "__main__":
    unittest.main()
