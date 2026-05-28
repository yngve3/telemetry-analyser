from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "telemetry-converter" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "telemetry-source" / "backend" / "src"))

from telemetry_converter import (  # noqa: E402
    ConversionError,
    TelemetryOutputFormat,
    UnifiedTelemetryPayload,
    convert,
    default_mavlink_stream_decoder,
)
from telemetry_source_backend.domain.common.models import TelemetrySample  # noqa: E402
from telemetry_source_backend.infrastructure.encoders.mavlink_encoder import (  # noqa: E402
    ATTITUDE_MSG_ID,
    GPS_RAW_INT_MSG_ID,
    GLOBAL_POSITION_INT_MSG_ID,
    HEARTBEAT_MSG_ID,
    MavlinkTelemetryEncoder,
    SYS_STATUS_MSG_ID,
)
from telemetry_source_backend.infrastructure.contracts.telemetry_contract import (  # noqa: E402
    TelemetryContractValidator,
)


class MavlinkConversionTest(unittest.TestCase):
    def test_converts_mavlink_stream_to_unified_telemetry(self) -> None:
        stream = MavlinkTelemetryEncoder(system_id=1, component_id=1).encode(
            self._sample()
        )

        telemetry = convert(stream)

        self.assertIsInstance(telemetry, UnifiedTelemetryPayload)
        self.assertEqual(telemetry.timestamp, datetime(2026, 5, 20, 12, 0, tzinfo=UTC))
        self.assertEqual(telemetry.drone_id, "uav-001")
        self.assertAlmostEqual(telemetry.latitude_deg, 47.397742, places=6)
        self.assertAlmostEqual(telemetry.longitude_deg, 8.545594, places=6)
        self.assertAlmostEqual(telemetry.altitude_m, 30.0)
        self.assertEqual(telemetry.battery_percent, 90.0)
        self.assertEqual(telemetry.satellites, 10)
        self.assertAlmostEqual(telemetry.ground_speed_m_s or 0.0, 8.0)
        self.assertAlmostEqual(telemetry.heading_deg or 0.0, 90.0)
        self.assertAlmostEqual(telemetry.yaw_rad or 0.0, 1.5708, places=4)
        self.assertEqual(telemetry.system_status, "active")
        self.assertEqual(telemetry.flight_mode, "auto")
        self.assertTrue(telemetry.armed)

    def test_converts_mavlink_stream_to_contract_dict(self) -> None:
        stream = MavlinkTelemetryEncoder(system_id=1, component_id=1).encode(
            self._sample()
        )

        payload = convert(
            stream,
            target_format=TelemetryOutputFormat.UNIFIED_TELEMETRY_DICT,
        )

        self.assertEqual(payload["timestamp"], "2026-05-20T12:00:00+00:00")
        self.assertEqual(payload["drone_id"], "uav-001")
        self.assertEqual(payload["battery_percent"], 90.0)
        self.assertEqual(payload["satellites"], 10)
        TelemetryContractValidator.load_default().validate_payload(payload)

    def test_rejects_corrupted_mavlink_checksum(self) -> None:
        stream = bytearray(
            MavlinkTelemetryEncoder(system_id=1, component_id=1).encode(self._sample())
        )
        stream[-1] ^= 0xFF

        with self.assertRaises(ConversionError):
            convert(bytes(stream))

    def test_stream_decoder_accumulates_multi_rate_frames(self) -> None:
        encoder = MavlinkTelemetryEncoder(system_id=1, component_id=1)
        decoder = default_mavlink_stream_decoder()
        initial_sample = self._sample()

        initial_frames = encoder.encode_messages_for_ids(
            initial_sample,
            (
                HEARTBEAT_MSG_ID,
                ATTITUDE_MSG_ID,
                GLOBAL_POSITION_INT_MSG_ID,
                GPS_RAW_INT_MSG_ID,
                SYS_STATUS_MSG_ID,
            ),
        )
        initial_outputs = [decoder.update(frame) for frame in initial_frames]

        self.assertTrue(all(output is None for output in initial_outputs[:-1]))
        initial_output = initial_outputs[-1]
        self.assertIsNotNone(initial_output)
        self.assertEqual(initial_output.battery_percent, 90.0)
        self.assertAlmostEqual(initial_output.yaw_rad or 0.0, 1.5708, places=4)

        attitude_sample = self._sample(
            timestamp=datetime(2026, 5, 20, 12, 0, 0, 20_000, tzinfo=UTC),
            yaw_rad=1.75,
        )
        attitude_output = decoder.update(
            encoder.encode_message(attitude_sample, ATTITUDE_MSG_ID)
        )

        self.assertIsNotNone(attitude_output)
        self.assertEqual(attitude_output.timestamp, attitude_sample.timestamp)
        self.assertEqual(attitude_output.battery_percent, 90.0)
        self.assertAlmostEqual(attitude_output.yaw_rad or 0.0, 1.75, places=4)

        position_sample = self._sample(
            timestamp=datetime(2026, 5, 20, 12, 0, 0, 100_000, tzinfo=UTC),
            latitude_deg=47.5,
        )
        position_output = decoder.update(
            encoder.encode_message(position_sample, GLOBAL_POSITION_INT_MSG_ID)
        )

        self.assertIsNotNone(position_output)
        self.assertEqual(position_output.timestamp, position_sample.timestamp)
        self.assertAlmostEqual(position_output.latitude_deg, 47.5)
        self.assertAlmostEqual(position_output.yaw_rad or 0.0, 1.75, places=4)
        self.assertEqual(position_output.battery_percent, 90.0)

        status_sample = self._sample(
            timestamp=datetime(2026, 5, 20, 12, 0, 0, 200_000, tzinfo=UTC),
            battery_percent=80.0,
        )
        status_output = decoder.update(
            encoder.encode_message(status_sample, SYS_STATUS_MSG_ID)
        )

        self.assertIsNotNone(status_output)
        self.assertEqual(status_output.timestamp, position_sample.timestamp)
        self.assertAlmostEqual(status_output.latitude_deg, 47.5)
        self.assertEqual(status_output.battery_percent, 80.0)

    def _sample(
        self,
        timestamp: datetime = datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
        latitude_deg: float = 47.397742,
        battery_percent: float = 90.0,
        yaw_rad: float = 1.5708,
    ) -> TelemetrySample:
        return TelemetrySample(
            timestamp=timestamp,
            drone_id="uav-001",
            latitude_deg=latitude_deg,
            longitude_deg=8.545594,
            altitude_m=30.0,
            battery_percent=battery_percent,
            satellites=10,
            ground_speed_m_s=8.0,
            vertical_speed_m_s=0.0,
            heading_deg=90.0,
            relative_altitude_m=30.0,
            roll_rad=0.0,
            pitch_rad=0.0,
            yaw_rad=yaw_rad,
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


if __name__ == "__main__":
    unittest.main()
