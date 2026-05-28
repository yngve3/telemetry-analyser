from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.domain.common.models import TelemetrySample  # noqa: E402
from telemetry_source_backend.domain.synthetic.models import (  # noqa: E402
    AnomalyProfile,
    AnomalyType,
)
from telemetry_source_backend.domain.synthetic.services.synthetic_telemetry_factory import (  # noqa: E402
    SyntheticTelemetryFactory,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection import (  # noqa: E402
    default_anomaly_registry,
)


class AnomalyInjectionTest(unittest.TestCase):
    def test_low_battery_anomaly_is_applied_by_registry(self) -> None:
        sample = TelemetrySample(
            timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
            drone_id="uav-001",
            latitude_deg=55.7558,
            longitude_deg=37.6173,
            altitude_m=120.0,
            battery_percent=80.0,
            satellites=10,
        )
        profile = AnomalyProfile(
            anomaly_type=AnomalyType.LOW_BATTERY,
            intensity=1.0,
        )

        result = SyntheticTelemetryFactory().apply_anomaly(sample, profile)

        self.assertEqual(result.battery_percent, 0.0)
        self.assertEqual(result.satellites, 10)

    def test_default_registry_contains_source_anomaly_set(self) -> None:
        registry = default_anomaly_registry()

        self.assertEqual(set(registry.injectors), set(AnomalyType))

    def test_gps_signal_loss_degrades_fix_quality(self) -> None:
        sample = self._sample()
        profile = AnomalyProfile(
            anomaly_type=AnomalyType.GPS_SIGNAL_LOSS,
            intensity=1.0,
        )

        result = SyntheticTelemetryFactory().apply_anomaly(sample, profile)

        self.assertEqual(result.satellites, 0)
        self.assertEqual(result.satellites_visible, 0)
        self.assertEqual(result.gps_fix_type, 1)
        self.assertGreater(result.gps_eph or 0.0, 1000.0)

    def test_imu_spike_is_preserved_after_derived_telemetry_update(self) -> None:
        sample = self._sample()
        profile = AnomalyProfile(
            anomaly_type=AnomalyType.IMU_SPIKE,
            intensity=1.0,
        )

        result = SyntheticTelemetryFactory().apply_anomaly(sample, profile)

        self.assertGreater(result.roll_rate_rad_s or 0.0, 0.0)
        self.assertLess(result.pitch_rate_rad_s or 0.0, 0.0)

    def _sample(self) -> TelemetrySample:
        return TelemetrySample(
            timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
            drone_id="uav-001",
            latitude_deg=55.7558,
            longitude_deg=37.6173,
            altitude_m=120.0,
            battery_percent=80.0,
            satellites=10,
            ground_speed_m_s=8.0,
            vertical_speed_m_s=0.0,
            heading_deg=90.0,
            roll_rad=0.0,
            pitch_rad=0.0,
            yaw_rad=1.5708,
            satellites_visible=10,
            gps_fix_type=3,
            gps_eph=100.0,
            gps_epv=150.0,
            battery_voltage_v=12.2,
            battery_current_a=8.0,
        )


if __name__ == "__main__":
    unittest.main()
