from __future__ import annotations

import unittest

from support import seconds_after, telemetry

from analysis_module.features import TelemetryHistory  # noqa: E402


class TelemetryHistoryTest(unittest.TestCase):
    def test_history_keeps_bounded_samples(self) -> None:
        history = TelemetryHistory(max_size=2)
        first = telemetry(timestamp=seconds_after(0))
        second = telemetry(timestamp=seconds_after(1))
        third = telemetry(timestamp=seconds_after(2))

        history.extend((first, second, third))

        self.assertEqual(history.samples(), (second, third))
        self.assertEqual(history.previous(), third)

    def test_recent_returns_samples_inside_time_window(self) -> None:
        history = TelemetryHistory(max_size=10)
        first = telemetry(timestamp=seconds_after(0))
        second = telemetry(timestamp=seconds_after(5))
        third = telemetry(timestamp=seconds_after(10))
        history.extend((first, second, third))

        self.assertEqual(history.recent(6, current_time=third.timestamp), (second, third))

    def test_rejects_non_positive_history_size(self) -> None:
        with self.assertRaises(ValueError):
            TelemetryHistory(max_size=0)


if __name__ == "__main__":
    unittest.main()
