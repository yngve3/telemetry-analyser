from __future__ import annotations

import base64
import socket
import sys
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "analysis-service" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "analysis-module" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "telemetry-converter" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "telemetry-source" / "backend" / "src"))

from analysis_service.presentation.api.app import create_app  # noqa: E402
from analysis_service.presentation.api.dependencies import (  # noqa: E402
    get_session_manager,
    reset_ingestion_manager,
)
from telemetry_source_backend.domain.common.models import TelemetrySample  # noqa: E402
from telemetry_source_backend.infrastructure.encoders.mavlink_encoder import (  # noqa: E402
    MavlinkTelemetryEncoder,
)


class AnalysisServiceApiTest(unittest.TestCase):
    def setUp(self) -> None:
        get_session_manager.cache_clear()
        reset_ingestion_manager()
        self._client_context = TestClient(create_app())
        self.client = self._client_context.__enter__()

    def tearDown(self) -> None:
        self._client_context.__exit__(None, None, None)

    def test_health_and_openapi_are_available(self) -> None:
        health_response = self.client.get("/health")
        openapi_response = self.client.get("/openapi.json")

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})
        self.assertEqual(openapi_response.status_code, 200)
        self.assertEqual(openapi_response.json()["info"]["title"], "Analysis Service")

    def test_model_discovery_lists_supported_models(self) -> None:
        response = self.client.get("/analysis/models")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = [item["name"] for item in payload["models"]]
        self.assertEqual(
            names,
            [
                "rule_based",
                "correlation_based",
                "isolation_forest",
                "autoencoder",
                "graph_based",
            ],
        )
        statuses = {item["name"]: item["status"] for item in payload["models"]}
        self.assertEqual(statuses["rule_based"], "available")
        self.assertEqual(statuses["correlation_based"], "available")
        self.assertEqual(statuses["isolation_forest"], "available")
        self.assertEqual(statuses["autoencoder"], "available")
        self.assertEqual(statuses["graph_based"], "planned")

    def test_detector_discovery_alias_uses_model_registry(self) -> None:
        response = self.client.get("/analysis/detectors")

        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.json()["detectors"]]
        self.assertEqual(
            names,
            [
                "rule_based",
                "correlation_based",
                "isolation_forest",
                "autoencoder",
                "graph_based",
            ],
        )

    def test_model_profile_discovery_lists_readiness(self) -> None:
        response = self.client.get("/analysis/model-profiles")

        self.assertEqual(response.status_code, 200)
        profiles = {item["name"]: item for item in response.json()["profiles"]}
        self.assertEqual(
            list(profiles),
            [
                "rules_only",
                "rules_with_correlation",
                "rules_with_isolation_forest",
                "full_hybrid",
            ],
        )
        self.assertEqual(profiles["rules_only"]["status"], "available")
        self.assertEqual(
            profiles["rules_with_correlation"]["status"],
            "available",
        )
        self.assertEqual(
            profiles["rules_with_correlation"]["unavailable_models"],
            [],
        )
        self.assertEqual(
            profiles["rules_with_isolation_forest"]["status"],
            "available",
        )
        self.assertEqual(
            profiles["rules_with_isolation_forest"]["unavailable_models"],
            [],
        )
        self.assertEqual(
            profiles["full_hybrid"]["status"],
            "available",
        )
        self.assertEqual(
            profiles["full_hybrid"]["unavailable_models"],
            [],
        )

    def test_profile_rejects_unknown_model(self) -> None:
        response = self.client.put(
            "/analysis/profile",
            json={"enabled_models": ["unknown"]},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("Unknown analysis model", response.json()["detail"])

    def test_profile_rejects_empty_model_list(self) -> None:
        response = self.client.put(
            "/analysis/profile",
            json={"enabled_models": []},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("At least one analysis model", response.json()["detail"])

    def test_profile_accepts_connected_model_profile(self) -> None:
        response = self.client.put(
            "/analysis/profile",
            json={"model_profile": "rules_with_correlation"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["enabled_models"],
            ["rule_based", "correlation_based"],
        )
        self.assertEqual(
            response.json()["enabled_detectors"],
            ["rule_based", "correlation_based"],
        )

    def test_session_can_be_created_read_and_deleted(self) -> None:
        create_response = self.client.post(
            "/analysis/sessions",
            json={"session_id": "uav-001"},
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["session_id"], "uav-001")
        self.assertEqual(
            create_response.json()["profile"]["model_profile"],
            "rules_only",
        )
        self.assertEqual(
            create_response.json()["profile"]["enabled_models"],
            ["rule_based"],
        )

        get_response = self.client.get("/analysis/sessions/uav-001")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["samples_analyzed"], 0)

        delete_response = self.client.delete("/analysis/sessions/uav-001")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["deleted"])

    def test_unified_telemetry_analysis_returns_module_result_shape(self) -> None:
        self.client.post("/analysis/sessions", json={"session_id": "uav-001"})

        response = self.client.post(
            "/analysis/sessions/uav-001/analyze",
            json={
                "format": "unified.telemetry",
                "telemetry": _telemetry_payload(battery_percent=20.0),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["has_anomalies"])
        self.assertEqual(payload["anomalies"][0]["type"], "LOW_BATTERY")
        self.assertIn("sources", payload["anomalies"][0])
        self.assertIn("rule_based", payload["detector_outputs"])

        state_response = self.client.get("/analysis/sessions/uav-001/state")
        self.assertEqual(state_response.status_code, 200)
        state_payload = state_response.json()
        self.assertEqual(
            state_payload["last_telemetry"]["battery_percent"],
            20.0,
        )
        self.assertEqual(
            state_payload["last_result"]["anomalies"][0]["type"],
            "LOW_BATTERY",
        )

    def test_session_history_is_kept_between_http_analysis_requests(self) -> None:
        self.client.post(
            "/analysis/sessions",
            json={
                "session_id": "history",
                "profile": {"enabled_rules": ["battery_drop"]},
            },
        )

        first_response = self.client.post(
            "/analysis/sessions/history/analyze",
            json={
                "format": "unified.telemetry",
                "telemetry": _telemetry_payload(
                    timestamp="2026-05-24T12:00:00+00:00",
                    battery_percent=90.0,
                ),
            },
        )
        second_response = self.client.post(
            "/analysis/sessions/history/analyze",
            json={
                "format": "unified.telemetry",
                "telemetry": _telemetry_payload(
                    timestamp="2026-05-24T12:00:02+00:00",
                    battery_percent=80.0,
                ),
            },
        )

        self.assertFalse(first_response.json()["has_anomalies"])
        self.assertEqual(
            second_response.json()["anomalies"][0]["type"],
            "BATTERY_DROP",
        )

    def test_mavlink_analysis_uses_telemetry_converter(self) -> None:
        self.client.post("/analysis/sessions", json={"session_id": "mavlink"})
        mavlink_payload = MavlinkTelemetryEncoder(
            system_id=1,
            component_id=1,
        ).encode(_sample())

        response = self.client.post(
            "/analysis/sessions/mavlink/analyze",
            json={
                "format": "mavlink.v2",
                "payload_base64": base64.b64encode(mavlink_payload).decode("ascii"),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["drone_id"], "uav-001")
        self.assertIn("rule_based", payload["detector_outputs"])

    def test_udp_mavlink_listener_analyzes_incoming_packets(self) -> None:
        port = _free_udp_port()
        self.client.post("/analysis/sessions", json={"session_id": "listener"})
        create_response = self.client.post(
            "/analysis/listeners",
            json={
                "session_id": "listener",
                "protocol": "udp",
                "format": "mavlink.v2",
                "bind_host": "127.0.0.1",
                "bind_port": port,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        listener_id = create_response.json()["listener_id"]

        active_response = self._wait_for_listener_status(listener_id, "active")
        self.assertEqual(active_response.status_code, 200)

        mavlink_payload = MavlinkTelemetryEncoder(
            system_id=1,
            component_id=1,
        ).encode(_sample())
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(mavlink_payload, ("127.0.0.1", port))

        status_response = self._wait_for_converted_samples(listener_id)
        payload = status_response.json()
        self.assertGreaterEqual(payload["received_packets"], 1)
        self.assertGreaterEqual(payload["converted_samples"], 1)
        self.assertIsNotNone(payload["last_result"])
        self.assertEqual(payload["last_result"]["drone_id"], "uav-001")

        last_result_response = self.client.get(
            "/analysis/sessions/listener/last-result"
        )
        self.assertEqual(last_result_response.status_code, 200)
        self.assertEqual(
            last_result_response.json()["result"]["drone_id"],
            "uav-001",
        )

        state_response = self.client.get("/analysis/sessions/listener/state")
        self.assertEqual(state_response.status_code, 200)
        state_payload = state_response.json()
        self.assertEqual(state_payload["last_telemetry"]["altitude_m"], 30.0)
        self.assertEqual(state_payload["last_telemetry"]["battery_percent"], 90.0)
        self.assertEqual(state_payload["last_telemetry"]["satellites"], 10)

        delete_response = self.client.delete(f"/analysis/listeners/{listener_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["deleted"])

    def test_deleting_session_stops_attached_listeners(self) -> None:
        port = _free_udp_port()
        self.client.post("/analysis/sessions", json={"session_id": "cleanup"})
        create_response = self.client.post(
            "/analysis/listeners",
            json={
                "session_id": "cleanup",
                "protocol": "udp",
                "format": "mavlink.v2",
                "bind_host": "127.0.0.1",
                "bind_port": port,
            },
        )
        listener_id = create_response.json()["listener_id"]

        delete_session_response = self.client.delete("/analysis/sessions/cleanup")

        self.assertEqual(delete_session_response.status_code, 200)
        listener_response = self.client.get(f"/analysis/listeners/{listener_id}")
        self.assertEqual(listener_response.status_code, 404)

    def test_listener_endpoint_conflict_is_rejected(self) -> None:
        port = _free_udp_port()
        self.client.post("/analysis/sessions", json={"session_id": "first"})
        self.client.post("/analysis/sessions", json={"session_id": "second"})
        first_response = self.client.post(
            "/analysis/listeners",
            json={
                "session_id": "first",
                "protocol": "udp",
                "format": "mavlink.v2",
                "bind_host": "127.0.0.1",
                "bind_port": port,
            },
        )
        self.assertEqual(first_response.status_code, 201)

        second_response = self.client.post(
            "/analysis/listeners",
            json={
                "session_id": "second",
                "protocol": "udp",
                "format": "mavlink.v2",
                "bind_host": "127.0.0.1",
                "bind_port": port,
            },
        )

        self.assertEqual(second_response.status_code, 422)
        self.assertIn("already exists", second_response.json()["detail"])

    def test_lifespan_shutdown_stops_active_listeners(self) -> None:
        port = _free_udp_port()
        get_session_manager.cache_clear()
        reset_ingestion_manager()
        with TestClient(create_app()) as client:
            client.post("/analysis/sessions", json={"session_id": "shutdown"})
            create_response = client.post(
                "/analysis/listeners",
                json={
                    "session_id": "shutdown",
                    "protocol": "udp",
                    "format": "mavlink.v2",
                    "bind_host": "127.0.0.1",
                    "bind_port": port,
                },
            )
            self.assertEqual(create_response.status_code, 201)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", port))

    def test_model_profile_controls_detector_outputs(self) -> None:
        create_response = self.client.post(
            "/analysis/sessions",
            json={
                "session_id": "hybrid",
                "profile": {"model_profile": "full_hybrid"},
            },
        )
        self.assertEqual(create_response.status_code, 201)

        response = self.client.post(
            "/analysis/sessions/hybrid/analyze",
            json={
                "format": "unified.telemetry",
                "telemetry": _telemetry_payload(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.json()["detector_outputs"]),
            [
                "rule_based",
                "correlation_based",
                "isolation_forest",
                "autoencoder",
            ],
        )

    def test_planned_model_is_rejected_during_session_creation(self) -> None:
        response = self.client.post(
            "/analysis/sessions",
            json={
                "session_id": "graph",
                "profile": {"enabled_models": ["graph_based"]},
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("graph_based", response.json()["detail"])

    def _wait_for_listener_status(self, listener_id: str, target_status: str):
        response = self.client.get(f"/analysis/listeners/{listener_id}")
        for _ in range(20):
            if response.json()["status"] == target_status:
                return response
            time.sleep(0.05)
            response = self.client.get(f"/analysis/listeners/{listener_id}")
        return response

    def _wait_for_converted_samples(self, listener_id: str):
        response = self.client.get(f"/analysis/listeners/{listener_id}")
        for _ in range(20):
            if response.json()["converted_samples"] >= 1:
                return response
            time.sleep(0.05)
            response = self.client.get(f"/analysis/listeners/{listener_id}")
        return response


def _telemetry_payload(
    timestamp: str = "2026-05-24T12:00:00+00:00",
    battery_percent: float = 90.0,
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "drone_id": "uav-001",
        "latitude_deg": 47.397742,
        "longitude_deg": 8.545594,
        "altitude_m": 30.0,
        "battery_percent": battery_percent,
        "satellites": 10,
        "ground_speed_m_s": 8.0,
        "heading_deg": 90.0,
    }


def _sample() -> TelemetrySample:
    return TelemetrySample(
        timestamp=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
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


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


if __name__ == "__main__":
    unittest.main()
