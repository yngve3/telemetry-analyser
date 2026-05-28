from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.presentation.api.app import create_app  # noqa: E402


class TranslationsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_translations_are_available_for_supported_languages(self) -> None:
        response = self.client.get("/translations")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["default_language"], "en")
        self.assertEqual(
            [language["code"] for language in payload["languages"]],
            ["en", "ru"],
        )
        self.assertEqual(payload["messages"]["en"]["routes.synthetic"], "Synthetic generator")
        self.assertEqual(payload["messages"]["ru"]["app.title"], "Источник телеметрии")
        self.assertEqual(payload["messages"]["ru"]["routes.synthetic"], "Синтетический генератор")
        self.assertIn("capability.websocket", payload["messages"]["en"])
        self.assertIn("capability.websocket", payload["messages"]["ru"])
        self.assertEqual(payload["messages"]["ru"]["common.host"], "Хост")
        self.assertEqual(payload["messages"]["ru"]["common.endpoint"], "Адрес")
        self.assertEqual(payload["messages"]["ru"]["common.active"], "Активен")
        self.assertEqual(payload["messages"]["ru"]["common.samples"], "Сообщения телеметрии")
        self.assertEqual(payload["messages"]["ru"]["snapshot.sampleCount.few"], "{count} сообщения")
        self.assertEqual(payload["messages"]["ru"]["synthetic.getSample"], "Получить сообщение")
        self.assertEqual(payload["messages"]["ru"]["synthetic.getBatch"], "Получить пакет")
        self.assertEqual(payload["messages"]["ru"]["synthetic.telemetryPreview"], "Предпросмотр телеметрии")
        self.assertEqual(payload["messages"]["ru"]["streams.streamPreview"], "Предпросмотр потока")
        self.assertEqual(payload["messages"]["ru"]["streams.preview"], "Просмотр")
        self.assertEqual(payload["messages"]["ru"]["snapshot.replayStream"], "Воспроизвести поток")
        self.assertEqual(payload["messages"]["ru"]["snapshot.stopStream"], "Остановить поток")
        self.assertEqual(payload["messages"]["ru"]["external.remote"], "Удалённый адрес")
        self.assertEqual(payload["messages"]["ru"]["anomaly.GPS_SPOOFING"], "GPS-спуфинг")
        self.assertEqual(payload["messages"]["ru"]["validation.hostRequired"], "Хост обязателен.")


if __name__ == "__main__":
    unittest.main()
