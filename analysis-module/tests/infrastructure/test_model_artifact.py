from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import ANALYSIS_MODULE_ROOT  # noqa: F401

from analysis_module.detectors.model_based import ModelArtifactError  # noqa: E402
from analysis_module.detectors.model_based.model_artifact import (  # noqa: E402
    ModelArtifactMetadata,
)
from analysis_module.features import TelemetryFeatureExtractor  # noqa: E402
from analysis_module.infrastructure.artifacts import (  # noqa: E402
    FilesystemModelArtifactRepository,
)


class ModelArtifactTest(unittest.TestCase):
    def test_metadata_validation_accepts_expected_feature_order(self) -> None:
        feature_names = TelemetryFeatureExtractor().feature_names

        metadata = ModelArtifactMetadata.from_dict(
            {
                "model_type": "autoencoder",
                "feature_version": "1.0",
                "window_size": 50,
                "feature_names": list(feature_names),
                "created_at": "2026-05-24T00:00:00Z",
            },
            expected_feature_names=feature_names,
        )

        self.assertEqual(metadata.model_type, "autoencoder")
        self.assertEqual(metadata.feature_names, feature_names)

    def test_metadata_validation_rejects_wrong_feature_order(self) -> None:
        with self.assertRaises(ModelArtifactError):
            ModelArtifactMetadata.from_dict(
                {
                    "model_type": "autoencoder",
                    "feature_version": "1.0",
                    "window_size": 50,
                    "feature_names": ["gps_eph", "battery_percent"],
                    "created_at": "2026-05-24T00:00:00Z",
                },
                expected_feature_names=TelemetryFeatureExtractor().feature_names,
            )

    def test_filesystem_repository_validates_artifact_directory(self) -> None:
        feature_names = TelemetryFeatureExtractor().feature_names
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory)
            (artifact_path / "model.pt").write_bytes(b"")
            _write_json(
                artifact_path / "metadata.json",
                {
                    "model_type": "autoencoder",
                    "feature_version": "1.0",
                    "window_size": 50,
                    "feature_names": list(feature_names),
                    "created_at": "2026-05-24T00:00:00Z",
                },
            )
            _write_json(artifact_path / "normalizer.json", {"type": "identity"})
            _write_json(artifact_path / "threshold.json", {"threshold": 0.75})

            model = FilesystemModelArtifactRepository().load(artifact_path)
            score = model.score(TelemetryFeatureExtractor().extract_window(()))

        self.assertEqual(score.threshold, 0.75)
        self.assertEqual(score.metadata["model_type"], "autoencoder")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
