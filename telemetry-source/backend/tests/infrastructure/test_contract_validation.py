from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.domain.common.models import TelemetrySample  # noqa: E402
from telemetry_source_backend.infrastructure.contracts.telemetry_contract import (  # noqa: E402
    TelemetryContractValidationError,
    TelemetryContractValidator,
)


class TelemetryContractValidatorTest(unittest.TestCase):
    def test_valid_sample_matches_shared_contract(self) -> None:
        validator = TelemetryContractValidator.load_default()

        validator.validate_sample(
            TelemetrySample(
                timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
                drone_id="uav-001",
                latitude_deg=47.397742,
                longitude_deg=8.545594,
                altitude_m=30.0,
                battery_percent=90.0,
                satellites=10,
            )
        )

    def test_valid_extended_sample_matches_shared_contract(self) -> None:
        validator = TelemetryContractValidator.load_default()

        validator.validate_sample(
            TelemetrySample(
                timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
                drone_id="uav-001",
                latitude_deg=47.397742,
                longitude_deg=8.545594,
                altitude_m=30.0,
                battery_percent=90.0,
                satellites=10,
                relative_altitude_m=30.0,
                velocity_x_m_s=8.0,
                velocity_y_m_s=0.0,
                velocity_z_m_s=0.0,
                roll_rad=0.0,
                pitch_rad=0.0,
                yaw_rad=1.5708,
                roll_rate_rad_s=0.0,
                pitch_rate_rad_s=0.0,
                yaw_rate_rad_s=0.0,
                satellites_visible=10,
                gps_fix_type=3,
                gps_eph=100.0,
                gps_epv=150.0,
                battery_voltage_v=12.2,
                battery_current_a=8.0,
                system_status="active",
                flight_mode="auto",
                armed=True,
                sensor_health_flags=0xFFFFFFFF,
            )
        )

    def test_invalid_battery_is_rejected(self) -> None:
        validator = TelemetryContractValidator.load_default()

        with self.assertRaises(TelemetryContractValidationError):
            validator.validate_sample(
                TelemetrySample(
                    timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
                    drone_id="uav-001",
                    latitude_deg=47.397742,
                    longitude_deg=8.545594,
                    altitude_m=30.0,
                    battery_percent=120.0,
                    satellites=10,
                )
            )


if __name__ == "__main__":
    unittest.main()
