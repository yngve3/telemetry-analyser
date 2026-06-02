from __future__ import annotations

import socket
import sys
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.presentation.api.app import create_app  # noqa: E402


class ExternalApiTest(unittest.TestCase):
    def test_external_udp_source_uses_compose_friendly_defaults(self) -> None:
        with TestClient(create_app()) as client:
            create_response = client.post(
                "/sources/external",
                json={"name": "external_mavlink"},
            )

        self.assertEqual(create_response.status_code, 201)
        status = create_response.json()["status"]
        self.assertEqual(status["address"], "0.0.0.0")
        self.assertEqual(status["port"], 14540)
        self.assertEqual(status["protocol"], "udp")
        self.assertTrue(status["forward_enabled"])
        self.assertEqual(status["forward_host"], "analysis-service")
        self.assertEqual(status["forward_port"], 14560)

    def test_external_udp_source_can_receive_packets(self) -> None:
        port = self._free_udp_port()
        with TestClient(create_app()) as client:
            create_response = client.post(
                "/sources/external",
                json={
                    "name": "external_mavlink",
                    "address": "127.0.0.1",
                    "port": port,
                    "protocol": "udp",
                    "forward_enabled": False,
                },
            )
            self.assertEqual(create_response.status_code, 201)
            source_id = create_response.json()["source_id"]

            start_response = client.post(f"/sources/external/{source_id}/start")
            self.assertEqual(start_response.status_code, 200)
            self.assertTrue(start_response.json()["is_active"])

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(b"mavlink-frame", ("127.0.0.1", port))

            status_payload = None
            for _ in range(20):
                status_response = client.get(f"/sources/external/{source_id}")
                status_payload = status_response.json()
                if status_payload["received_packets"] >= 1:
                    break
                time.sleep(0.05)

            stop_response = client.post(f"/sources/external/{source_id}/stop")
            self.assertEqual(stop_response.status_code, 200)
            self.assertFalse(stop_response.json()["is_active"])

        self.assertIsNotNone(status_payload)
        self.assertGreaterEqual(status_payload["received_packets"], 1)
        self.assertEqual(status_payload["last_payload_size"], len(b"mavlink-frame"))
        self.assertEqual(status_payload["last_payload_preview_ascii"], "mavlink-frame")
        self.assertEqual(
            status_payload["last_payload_preview_hex"],
            b"mavlink-frame".hex(" "),
        )
        self.assertFalse(status_payload["last_payload_preview_truncated"])
        self.assertEqual(status_payload["forwarded_packets"], 0)
        self.assertIsNone(status_payload["last_error"])
        self.assertIsNone(status_payload["last_forward_error"])

    def test_external_udp_source_forwards_packets(self) -> None:
        external_port = self._free_udp_port()
        payload = b"mavlink-frame"

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as forward_sock:
            forward_sock.bind(("127.0.0.1", 0))
            forward_sock.settimeout(2)
            forward_port = forward_sock.getsockname()[1]

            with TestClient(create_app()) as client:
                create_response = client.post(
                    "/sources/external",
                    json={
                        "name": "external_mavlink",
                        "address": "127.0.0.1",
                        "port": external_port,
                        "protocol": "udp",
                        "forward_enabled": True,
                        "forward_host": "127.0.0.1",
                        "forward_port": forward_port,
                    },
                )
                self.assertEqual(create_response.status_code, 201)
                source_id = create_response.json()["source_id"]

                start_response = client.post(f"/sources/external/{source_id}/start")
                self.assertEqual(start_response.status_code, 200)
                self.assertTrue(start_response.json()["is_active"])

                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(payload, ("127.0.0.1", external_port))

                forwarded_payload, _ = forward_sock.recvfrom(4096)
                status_payload = None
                for _ in range(20):
                    status_response = client.get(f"/sources/external/{source_id}")
                    status_payload = status_response.json()
                    if status_payload["forwarded_packets"] >= 1:
                        break
                    time.sleep(0.05)

                stop_response = client.post(f"/sources/external/{source_id}/stop")
                self.assertEqual(stop_response.status_code, 200)

        self.assertEqual(forwarded_payload, payload)
        self.assertIsNotNone(status_payload)
        self.assertGreaterEqual(status_payload["received_packets"], 1)
        self.assertGreaterEqual(status_payload["forwarded_packets"], 1)
        self.assertIsNone(status_payload["last_forward_error"])

    def test_external_udp_source_can_be_deleted(self) -> None:
        port = self._free_udp_port()
        with TestClient(create_app()) as client:
            create_response = client.post(
                "/sources/external",
                json={
                    "name": "external_mavlink",
                    "address": "127.0.0.1",
                    "port": port,
                    "protocol": "udp",
                    "forward_enabled": False,
                },
            )
            self.assertEqual(create_response.status_code, 201)
            source_id = create_response.json()["source_id"]

            start_response = client.post(f"/sources/external/{source_id}/start")
            self.assertEqual(start_response.status_code, 200)

            delete_response = client.delete(f"/sources/external/{source_id}")
            self.assertEqual(delete_response.status_code, 200)
            self.assertTrue(delete_response.json()["deleted"])

            status_response = client.get(f"/sources/external/{source_id}")

        self.assertEqual(status_response.status_code, 404)

    def _free_udp_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]


if __name__ == "__main__":
    unittest.main()
