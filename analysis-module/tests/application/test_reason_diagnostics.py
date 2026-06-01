from __future__ import annotations

import unittest

from support import ANALYSIS_MODULE_ROOT  # noqa: F401

from analysis_module.application.reason_diagnostics import (  # noqa: E402
    FeatureStatistics,
    ReasonDiagnostics,
)


class ReasonDiagnosticsTest(unittest.TestCase):
    def test_gps_reason_is_selected_for_eph_and_epv_deviation(self) -> None:
        result = ReasonDiagnostics().diagnose(
            {
                "eph_mean": 12.0,
                "epv_mean": 10.0,
                "altitude_delta": 1.0,
            },
            _statistics("eph_mean", "epv_mean", "altitude_delta"),
        )

        self.assertEqual(result.reasons[0].group, "GPS")
        self.assertIn("eph_mean", result.reasons[0].features)

    def test_altitude_reason_is_selected_for_height_deviation(self) -> None:
        result = ReasonDiagnostics().diagnose(
            {
                "altitude_delta": 20.0,
                "hgt_test_ratio_max": 7.0,
                "eph_mean": 1.0,
            },
            _statistics("altitude_delta", "hgt_test_ratio_max", "eph_mean"),
        )

        self.assertEqual(result.reasons[0].group, "Altitude")

    def test_battery_reason_is_selected_for_battery_warning(self) -> None:
        result = ReasonDiagnostics().diagnose(
            {
                "battery_warning_max": 4.0,
                "battery_voltage_mean": 0.2,
            },
            _statistics("battery_warning_max", "battery_voltage_mean"),
        )

        self.assertEqual(result.reasons[0].group, "Battery")

    def test_failsafe_reason_is_selected_for_failure_flags(self) -> None:
        result = ReasonDiagnostics().diagnose(
            {
                "fd_critical_failure_max": 5.0,
                "local_position_invalid_max": 3.0,
            },
            _statistics("fd_critical_failure_max", "local_position_invalid_max"),
        )

        self.assertEqual(result.reasons[0].group, "Failsafe")


def _statistics(*names: str) -> dict[str, FeatureStatistics]:
    return {
        name: FeatureStatistics(mean=0.0, std=1.0, minimum=0.0, maximum=1.0)
        for name in names
    }


if __name__ == "__main__":
    unittest.main()
