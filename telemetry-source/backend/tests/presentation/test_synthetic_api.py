from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.presentation.api.app import create_app  # noqa: E402


class SyntheticApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_openapi_is_available(self) -> None:
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["info"]["title"], "Telemetry Source")

    def test_synthetic_mission_can_be_created_started_and_sampled(self) -> None:
        create_response = self.client.post(
            "/sources/synthetic/missions",
            json=self._mission_payload(),
        )
        self.assertEqual(create_response.status_code, 201)
        mission_id = create_response.json()["mission_id"]

        start_response = self.client.post(
            f"/sources/synthetic/missions/{mission_id}/start"
        )
        self.assertEqual(start_response.status_code, 200)
        self.assertTrue(start_response.json()["is_running"])

        batch_response = self.client.get(
            f"/sources/synthetic/missions/{mission_id}/samples",
            params={"count": 3},
        )
        self.assertEqual(batch_response.status_code, 200)
        samples = batch_response.json()
        self.assertEqual(len(samples), 3)
        self.assertEqual(samples[0]["drone_id"], "uav-001")
        self.assertIn("roll_rad", samples[0])
        self.assertIn("gps_fix_type", samples[0])
        self.assertIn("battery_voltage_v", samples[0])
        self.assertIn("system_status", samples[0])

    def test_synthetic_mission_accepts_anomaly_command(self) -> None:
        mission_id = self.client.post(
            "/sources/synthetic/missions",
            json=self._mission_payload(),
        ).json()["mission_id"]
        self.client.post(f"/sources/synthetic/missions/{mission_id}/start")

        response = self.client.post(
            f"/sources/synthetic/missions/{mission_id}/commands",
            json={
                "command": "inject_anomaly",
                "type": "GPS_SPOOFING",
                "start_after_sec": 0,
                "duration_sec": 5,
                "intensity": 0.7,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scheduled_anomalies_count"], 1)

    def test_synthetic_mission_can_start_and_stop_udp_stream(self) -> None:
        mission_id = self.client.post(
            "/sources/synthetic/missions",
            json=self._mission_payload(),
        ).json()["mission_id"]

        response = self.client.post(
            f"/streams/synthetic/missions/{mission_id}/udp",
            json={"host": "127.0.0.1", "port": 14551, "frequency_hz": 50},
        )
        self.assertEqual(response.status_code, 201)
        stream_id = response.json()["stream_id"]
        self.assertTrue(response.json()["is_active"])

        time.sleep(0.05)

        preview_response = self._wait_for_preview_samples(
            f"/streams/udp/{stream_id}/preview"
        )
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.json()["stream_id"], stream_id)
        self.assertGreaterEqual(len(preview_response.json()["samples"]), 1)
        self.assertEqual(preview_response.json()["samples"][0]["drone_id"], "uav-001")

        stop_response = self.client.delete(f"/streams/udp/{stream_id}")
        self.assertEqual(stop_response.status_code, 200)
        self.assertFalse(stop_response.json()["is_active"])

    def _mission_payload(self) -> dict[str, object]:
        return {
            "name": "simple_mission",
            "frequency_hz": 20,
            "home": {
                "latitude": 47.397742,
                "longitude": 8.545594,
                "altitude": 0,
                "heading_deg": 0,
                "battery": 100,
            },
            "steps": [
                {"type": "takeoff", "target_altitude": 30},
                {"type": "move_forward", "distance_m": 100, "speed_m_s": 8},
                {"type": "turn", "direction": "right", "angle_deg": 90},
                {"type": "move_forward", "distance_m": 80, "speed_m_s": 8},
                {"type": "hover", "duration_sec": 10},
                {"type": "return_home", "speed_m_s": 8},
                {"type": "landing"},
            ],
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
