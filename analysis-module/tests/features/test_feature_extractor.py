from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module.features import TelemetryFeatureExtractor  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
