"""Filesystem repository for telemetry model artifact packages."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from analysis_module.detectors.model_based.interfaces import TelemetryScoringModel
from analysis_module.detectors.model_based.model_artifact import (
    ModelArtifact,
    ModelArtifactError,
    parse_model_artifact,
)
from analysis_module.detectors.model_based.neural_models import (
    AutoencoderArtifactScoringModel,
)
from analysis_module.features.feature_extractor import TelemetryFeatureExtractor


@dataclass(frozen=True, slots=True)
class FilesystemModelArtifactRepository:
    """Validates model artifact packages from a directory or zip file."""

    expected_feature_names: Sequence[str] = field(
        default_factory=lambda: TelemetryFeatureExtractor().feature_names
    )

    def load(self, path: str | Path) -> TelemetryScoringModel:
        artifact_path = Path(path)
        if artifact_path.is_dir():
            artifact = self._load_directory(artifact_path)
        elif artifact_path.is_file() and artifact_path.suffix.lower() == ".zip":
            artifact = self._load_zip(artifact_path)
        else:
            raise ModelArtifactError(
                "Model artifact path must be a directory or a .zip file."
            )

        return AutoencoderArtifactScoringModel(
            threshold=artifact.threshold,
            metadata=artifact.metadata.to_dict(),
        )

    def _load_directory(self, artifact_path: Path) -> ModelArtifact:
        required_files = (
            "model.pt",
            "metadata.json",
            "normalizer.json",
            "threshold.json",
        )
        for file_name in required_files:
            if not (artifact_path / file_name).is_file():
                raise ModelArtifactError(
                    f"Model artifact is missing required file `{file_name}`."
                )

        return parse_model_artifact(
            metadata_payload=_read_json_file(artifact_path / "metadata.json"),
            threshold_payload=_read_json_file(artifact_path / "threshold.json"),
            normalizer_payload=_read_json_file(artifact_path / "normalizer.json"),
            expected_feature_names=self.expected_feature_names,
        )

    def _load_zip(self, artifact_path: Path) -> ModelArtifact:
        with ZipFile(artifact_path) as archive:
            for file_name in (
                "model.pt",
                "metadata.json",
                "normalizer.json",
                "threshold.json",
            ):
                if _find_zip_member(archive, file_name) is None:
                    raise ModelArtifactError(
                        f"Model artifact is missing required file `{file_name}`."
                    )

            return parse_model_artifact(
                metadata_payload=_read_zip_json(archive, "metadata.json"),
                threshold_payload=_read_zip_json(archive, "threshold.json"),
                normalizer_payload=_read_zip_json(archive, "normalizer.json"),
                expected_feature_names=self.expected_feature_names,
            )


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise ModelArtifactError(f"Artifact file `{path.name}` is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ModelArtifactError(f"Artifact file `{path.name}` must contain an object.")
    return payload


def _read_zip_json(archive: ZipFile, file_name: str) -> dict[str, Any]:
    member = _find_zip_member(archive, file_name)
    if member is None:
        raise ModelArtifactError(f"Model artifact is missing required file `{file_name}`.")

    try:
        with archive.open(member) as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise ModelArtifactError(f"Artifact file `{file_name}` is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ModelArtifactError(f"Artifact file `{file_name}` must contain an object.")
    return payload


def _find_zip_member(archive: ZipFile, file_name: str) -> str | None:
    for member in archive.namelist():
        normalized = member.rstrip("/")
        if normalized == file_name or normalized.endswith(f"/{file_name}"):
            return member
    return None
