from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.domain.common.models import TelemetrySample  # noqa: E402
from telemetry_source_backend.infrastructure.encoders.mavlink_encoder import (  # noqa: E402
    ATTITUDE_MSG_ID,
    GPS_RAW_INT_MSG_ID,
    GLOBAL_POSITION_INT_MSG_ID,
    HEARTBEAT_MSG_ID,
    MAVLINK_V2_MAGIC,
    MavlinkStreamRateScheduler,
    MavlinkTelemetryEncoder,
    SYS_STATUS_MSG_ID,
)


class MavlinkTelemetryEncoderTest(unittest.TestCase):
    def test_encodes_required_telemetry_subset(self) -> None:
        encoder = MavlinkTelemetryEncoder(system_id=1, component_id=1)

        frames = encoder.encode_messages(
            TelemetrySample(
                timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
                drone_id="uav-001",
                latitude_deg=47.397742,
                longitude_deg=8.545594,
                altitude_m=30.0,
                battery_percent=90.0,
                satellites=10,
                ground_speed_m_s=8.0,
                vertical_speed_m_s=0.0,
                heading_deg=90.0,
                relative_altitude_m=30.0,
                roll_rad=0.0,
                pitch_rad=0.0,
                yaw_rad=1.5708,
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

        self.assertEqual(
            [_message_id(frame) for frame in frames],
            [
                HEARTBEAT_MSG_ID,
                ATTITUDE_MSG_ID,
                GLOBAL_POSITION_INT_MSG_ID,
                GPS_RAW_INT_MSG_ID,
                SYS_STATUS_MSG_ID,
            ],
        )
        self.assertEqual([frame[1] for frame in frames], [9, 28, 28, 30, 31])
        self.assertTrue(all(frame[0] == MAVLINK_V2_MAGIC for frame in frames))

    def test_encode_returns_concatenated_mavlink_stream(self) -> None:
        encoder = MavlinkTelemetryEncoder()
        stream = encoder.encode(self._sample())

        frames = _split_frames(stream)

        self.assertEqual(len(frames), 5)
        self.assertEqual(_message_id(frames[0]), HEARTBEAT_MSG_ID)
        self.assertEqual(_message_id(frames[-1]), SYS_STATUS_MSG_ID)

    def test_sequence_increments(self) -> None:
        encoder = MavlinkTelemetryEncoder()
        sample = self._sample()

        first_batch = encoder.encode_messages(sample)
        second_batch = encoder.encode_messages(sample)

        self.assertEqual([frame[4] for frame in first_batch], [0, 1, 2, 3, 4])
        self.assertEqual([frame[4] for frame in second_batch], [5, 6, 7, 8, 9])

    def test_stream_rate_scheduler_separates_message_rates(self) -> None:
        scheduler = MavlinkStreamRateScheduler()
        counts: dict[int, int] = {}

        for _ in range(50):
            for message_id in scheduler.due_message_ids(0.02):
                counts[message_id] = counts.get(message_id, 0) + 1

        self.assertEqual(counts[HEARTBEAT_MSG_ID], 1)
        self.assertEqual(counts[SYS_STATUS_MSG_ID], 1)
        self.assertEqual(counts[GPS_RAW_INT_MSG_ID], 5)
        self.assertEqual(counts[GLOBAL_POSITION_INT_MSG_ID], 10)
        self.assertEqual(counts[ATTITUDE_MSG_ID], 50)

    def test_can_encode_selected_stream_messages_without_sequence_gaps(self) -> None:
        encoder = MavlinkTelemetryEncoder()
        frames = encoder.encode_messages_for_ids(
            self._sample(),
            (HEARTBEAT_MSG_ID, ATTITUDE_MSG_ID, ATTITUDE_MSG_ID),
        )

        self.assertEqual(
            [_message_id(frame) for frame in frames],
            [HEARTBEAT_MSG_ID, ATTITUDE_MSG_ID, ATTITUDE_MSG_ID],
        )
        self.assertEqual([frame[4] for frame in frames], [0, 1, 2])

    def _sample(self) -> TelemetrySample:
        return TelemetrySample(
            timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
            drone_id="uav-001",
            latitude_deg=47.397742,
            longitude_deg=8.545594,
            altitude_m=30.0,
            battery_percent=90.0,
            satellites=10,
            ground_speed_m_s=8.0,
            vertical_speed_m_s=0.0,
            heading_deg=90.0,
        )


def _message_id(frame: bytes) -> int:
    return frame[7] | (frame[8] << 8) | (frame[9] << 16)


def _split_frames(stream: bytes) -> list[bytes]:
    frames: list[bytes] = []
    cursor = 0
    while cursor < len(stream):
        payload_length = stream[cursor + 1]
        frame_length = 10 + payload_length + 2
        frames.append(stream[cursor : cursor + frame_length])
        cursor += frame_length
    return frames


if __name__ == "__main__":
    unittest.main()
