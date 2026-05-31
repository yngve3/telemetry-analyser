from __future__ import annotations

import base64
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "analysis-service" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "analysis-module" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "telemetry-converter" / "src"))

from analysis_service.presentation.api.app import create_app  # noqa: E402
from analysis_service.presentation.api.dependencies import (  # noqa: E402
    get_session_manager,
    reset_ingestion_manager,
)


class InvalidTelemetryInputTest(unittest.TestCase):
    def setUp(self) -> None:
        get_session_manager.cache_clear()
        reset_ingestion_manager()
        self._client_context = TestClient(create_app())
        self.client = self._client_context.__enter__()
        self.client.post("/analysis/sessions", json={"session_id": "uav-001"})

    def tearDown(self) -> None:
        self._client_context.__exit__(None, None, None)

    def test_empty_json_is_rejected(self) -> None:
        response = self.client.post("/analysis/sessions/uav-001/analyze", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("telemetry", response.json()["detail"])

    def test_missing_timestamp_is_rejected(self) -> None:
        telemetry = _valid_telemetry()
        telemetry.pop("timestamp")

        response = self._post_telemetry(telemetry)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"][0]["field"], "timestamp")

    def test_latitude_out_of_range_is_rejected(self) -> None:
        response = self._post_telemetry(_valid_telemetry(latitude_deg=999.0))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"][0]["field"], "latitude_deg")

    def test_battery_below_range_is_rejected(self) -> None:
        response = self._post_telemetry(_valid_telemetry(battery_percent=-10.0))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"][0]["field"], "battery_percent")

    def test_battery_above_range_is_rejected(self) -> None:
        response = self._post_telemetry(_valid_telemetry(battery_percent=150.0))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"][0]["field"], "battery_percent")

    def test_invalid_altitude_type_is_rejected(self) -> None:
        response = self._post_telemetry(_valid_telemetry(altitude_m="abc"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"][0]["field"], "altitude_m")

    def test_unreasonable_altitude_is_rejected(self) -> None:
        response = self._post_telemetry(_valid_telemetry(altitude_m=200_000.0))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"][0]["field"], "altitude_m")

    def test_invalid_attitude_angle_is_rejected(self) -> None:
        response = self._post_telemetry(_valid_telemetry(roll_rad=99.0))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"][0]["field"], "roll_rad")

    def test_nan_and_infinity_values_are_rejected(self) -> None:
        request = {
            "format": "unified.telemetry",
            "telemetry": _valid_telemetry(
                ground_speed_m_s=float("nan"),
                vertical_speed_m_s=float("inf"),
            ),
        }

        response = self.client.post(
            "/analysis/sessions/uav-001/analyze",
            content=json.dumps(request, allow_nan=True),
            headers={"content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 400)
        fields = {item["field"] for item in response.json()["detail"]}
        self.assertIn("ground_speed_m_s", fields)
        self.assertIn("vertical_speed_m_s", fields)

    def test_large_mavlink_payload_is_rejected(self) -> None:
        response = self.client.post(
            "/analysis/sessions/uav-001/analyze",
            json={
                "format": "mavlink.v2",
                "payload_base64": base64.b64encode(b"x" * 70_000).decode("ascii"),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("too large", response.json()["detail"])

    def test_unknown_telemetry_fields_are_rejected(self) -> None:
        telemetry = _valid_telemetry(unknown_field="value")

        response = self._post_telemetry(telemetry)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"][0]["field"], "unknown_field")

    def test_malformed_mavlink_base64_is_rejected(self) -> None:
        response = self.client.post(
            "/analysis/sessions/uav-001/analyze",
            json={
                "format": "mavlink.v2",
                "payload_base64": "not-base64",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("base64", response.json()["detail"])

    def test_corrupted_mavlink_payload_is_rejected(self) -> None:
        response = self.client.post(
            "/analysis/sessions/uav-001/analyze",
            json={
                "format": "mavlink.v2",
                "payload_base64": base64.b64encode(b"broken").decode("ascii"),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("decode", response.json()["detail"])

    def _post_telemetry(self, telemetry: dict[str, Any]):
        return self.client.post(
            "/analysis/sessions/uav-001/analyze",
            json={
                "format": "unified.telemetry",
                "telemetry": telemetry,
            },
        )


def _valid_telemetry(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": "2026-05-24T12:00:00+00:00",
        "drone_id": "uav-001",
        "latitude_deg": 47.397742,
        "longitude_deg": 8.545594,
        "altitude_m": 30.0,
        "battery_percent": 90.0,
        "satellites": 10,
        "ground_speed_m_s": 8.0,
        "heading_deg": 90.0,
    }
    result = deepcopy(payload)
    result.update(overrides)
    return result


if __name__ == "__main__":
    unittest.main()
