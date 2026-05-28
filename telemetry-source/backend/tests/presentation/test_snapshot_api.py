from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.presentation.api.app import create_app  # noqa: E402


class SnapshotApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_snapshot_can_be_uploaded_and_read(self) -> None:
        create_response = self.client.post(
            "/sources/snapshots",
            json=self._snapshot_payload(),
        )

        self.assertEqual(create_response.status_code, 201)
        snapshot_id = create_response.json()["snapshot_id"]
        self.assertEqual(create_response.json()["status"]["samples_count"], 2)

        samples_response = self.client.get(f"/sources/snapshots/{snapshot_id}/samples")

        self.assertEqual(samples_response.status_code, 200)
        self.assertEqual(len(samples_response.json()["samples"]), 2)

    def test_snapshot_can_be_sent_once_over_udp(self) -> None:
        snapshot_id = self.client.post(
            "/sources/snapshots",
            json=self._snapshot_payload(),
        ).json()["snapshot_id"]

        response = self.client.post(
            f"/sources/snapshots/{snapshot_id}/send-once/udp",
            json={"host": "127.0.0.1", "port": 14552},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["samples_sent"], 2)
        self.assertEqual(response.json()["frames_sent"], 10)

    def test_snapshot_can_start_and_stop_udp_replay_stream(self) -> None:
        snapshot_id = self.client.post(
            "/sources/snapshots",
            json=self._snapshot_payload(),
        ).json()["snapshot_id"]

        response = self.client.post(
            f"/streams/snapshots/{snapshot_id}/udp",
            json={"host": "127.0.0.1", "port": 14553, "frequency_hz": 50, "repeat": True},
        )
        self.assertEqual(response.status_code, 201)
        stream_id = response.json()["stream_id"]
        self.assertTrue(response.json()["is_active"])

        time.sleep(0.05)

        preview_response = self._wait_for_preview_samples(
            f"/streams/snapshots/udp/{stream_id}/preview"
        )
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.json()["stream_id"], stream_id)
        self.assertGreaterEqual(len(preview_response.json()["samples"]), 1)
        self.assertEqual(preview_response.json()["samples"][0]["drone_id"], "uav-001")

        stop_response = self.client.delete(f"/streams/snapshots/udp/{stream_id}")
        self.assertEqual(stop_response.status_code, 200)
        self.assertFalse(stop_response.json()["is_active"])

    def _snapshot_payload(self) -> dict[str, object]:
        return {
            "name": "short_snapshot",
            "interval_seconds": 0.1,
            "repeat": False,
            "samples": [
                self._sample("2026-05-20T12:00:00+00:00", 30.0),
                self._sample("2026-05-20T12:00:01+00:00", 31.0),
            ],
        }

    def _sample(self, timestamp: str, altitude_m: float) -> dict[str, object]:
        return {
            "timestamp": timestamp,
            "drone_id": "uav-001",
            "latitude_deg": 47.397742,
            "longitude_deg": 8.545594,
            "altitude_m": altitude_m,
            "battery_percent": 90.0,
            "satellites": 10,
            "ground_speed_m_s": 8.0,
            "vertical_speed_m_s": 0.0,
            "heading_deg": 90.0,
            "relative_altitude_m": altitude_m,
            "roll_rad": 0.0,
            "pitch_rad": 0.0,
            "yaw_rad": 1.5708,
            "satellites_visible": 10,
            "gps_fix_type": 3,
            "gps_eph": 100.0,
            "gps_epv": 150.0,
            "battery_voltage_v": 12.2,
            "battery_current_a": 8.0,
            "system_status": "active",
            "flight_mode": "auto",
            "armed": True,
            "sensor_health_flags": 4294967295,
        }

    def _wait_for_preview_samples(self, path: str):
        response = self.client.get(path)
        for _ in range(10):
            if response.json()["samples"]:
                return response
            time.sleep(0.05)
            response = self.client.get(path)
        return response


if __name__ == "__main__":
    unittest.main()
