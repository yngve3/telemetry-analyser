from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module import AnomalyType, Severity  # noqa: E402
from analysis_module.detectors.rule_based.rules import (  # noqa: E402
    BatteryDropRule,
    GpsSignalLossRule,
    GpsSpoofingRule,
    ImuSpikeRule,
    ImpossibleAltitudeRule,
    LowBatteryRule,
    MotionInconsistencyRule,
    TelemetryFreezeRule,
    TelemetryGapRule,
)
from analysis_module.features import TelemetryHistory  # noqa: E402


class RuleBasedRulesTest(unittest.TestCase):
    def test_gps_signal_loss_rule_detects_no_satellites(self) -> None:
        anomaly = GpsSignalLossRule().evaluate(
            telemetry(satellites=0, satellites_visible=0),
            TelemetryHistory(),
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.GPS_SIGNAL_LOSS)
        self.assertEqual(anomaly.severity, Severity.CRITICAL)

    def test_gps_spoofing_rule_detects_large_position_jump(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = GpsSpoofingRule().evaluate(
            telemetry(
                timestamp=seconds_after(1),
                latitude_deg=55.7758,
                ground_speed_m_s=8.0,
            ),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.GPS_SPOOFING)
        self.assertIn("distance_delta_m", anomaly.evidence)

    def test_gps_spoofing_rule_uses_previous_sample_with_elapsed_time(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))
        history.append(telemetry(timestamp=seconds_after(1)))

        anomaly = GpsSpoofingRule().evaluate(
            telemetry(
                timestamp=seconds_after(1),
                latitude_deg=55.7758,
                ground_speed_m_s=8.0,
            ),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.GPS_SPOOFING)

    def test_imu_spike_rule_detects_angular_rate_spike(self) -> None:
        anomaly = ImuSpikeRule().evaluate(
            telemetry(roll_rate_rad_s=8.0),
            TelemetryHistory(),
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.IMU_SPIKE)

    def test_battery_drop_rule_detects_abrupt_drop(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0), battery_percent=90.0))

        anomaly = BatteryDropRule().evaluate(
            telemetry(timestamp=seconds_after(2), battery_percent=80.0),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.BATTERY_DROP)

    def test_low_battery_rule_detects_low_charge(self) -> None:
        anomaly = LowBatteryRule().evaluate(
            telemetry(battery_percent=10.0),
            TelemetryHistory(),
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.LOW_BATTERY)
        self.assertEqual(anomaly.severity, Severity.CRITICAL)

    def test_impossible_altitude_rule_detects_out_of_range_altitude(self) -> None:
        anomaly = ImpossibleAltitudeRule().evaluate(
            telemetry(altitude_m=31_000.0),
            TelemetryHistory(),
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.IMPOSSIBLE_ALTITUDE)

    def test_telemetry_freeze_rule_detects_unchanged_telemetry(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = TelemetryFreezeRule().evaluate(
            telemetry(timestamp=seconds_after(6)),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.TELEMETRY_FREEZE)

    def test_telemetry_gap_rule_detects_large_time_gap(self) -> None:
        history = TelemetryHistory()
        history.append(telemetry(timestamp=seconds_after(0)))

        anomaly = TelemetryGapRule(max_elapsed_sec=10.0).evaluate(
            telemetry(timestamp=seconds_after(20)),
            history,
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.TELEMETRY_GAP)

    def test_motion_inconsistency_rule_detects_speed_mismatch(self) -> None:
        anomaly = MotionInconsistencyRule().evaluate(
            telemetry(
                ground_speed_m_s=5.0,
                velocity_x_m_s=20.0,
                velocity_y_m_s=0.0,
            ),
            TelemetryHistory(),
        )

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.type, AnomalyType.MOTION_INCONSISTENCY)


if __name__ == "__main__":
    unittest.main()
