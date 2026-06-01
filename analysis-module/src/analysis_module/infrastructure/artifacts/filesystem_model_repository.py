"""Filesystem repository for telemetry model artifact packages."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from analysis_module.application.reason_diagnostics import (
    feature_statistics_from_metadata,
)
from analysis_module.detectors.model_based.interfaces import TelemetryScoringModel
from analysis_module.detectors.model_based.model_artifact import (
    ModelArtifact,
    ModelArtifactError,
    parse_model_artifact,
)
from analysis_module.detectors.model_based.neural_models import (
    AutoencoderArtifactScoringModel,
)
from analysis_module.features.model_features import SEQUENCE_FEATURE_NAMES


@dataclass(frozen=True, slots=True)
class FilesystemModelArtifactRepository:
    """Validates model artifact packages from a directory or zip file."""

    expected_feature_names: Sequence[str] = field(
        default_factory=lambda: SEQUENCE_FEATURE_NAMES
    )

    def load(self, path: str | Path) -> TelemetryScoringModel:
        artifact_path = Path(path)
        if artifact_path.is_dir():
            if (artifact_path / "scaler.joblib").is_file():
                return self._load_torch_directory(artifact_path)
            artifact = self._load_legacy_directory(artifact_path)
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

    def _load_torch_directory(self, artifact_path: Path) -> AutoencoderArtifactScoringModel:
        for file_name in ("model.pt", "metadata.json", "scaler.joblib"):
            if not (artifact_path / file_name).is_file():
                raise ModelArtifactError(
                    f"Model artifact is missing required file `{file_name}`."
                )

        metadata = _read_json_file(artifact_path / "metadata.json")
        if metadata.get("model_type") not in ("mlp_autoencoder", "autoencoder"):
            raise ModelArtifactError(
                "Autoencoder artifact metadata has an invalid model_type."
            )

        feature_names = _required_str_tuple(metadata, "feature_names")
        window_size = _required_positive_int(metadata, "window_size")
        threshold = _required_number(metadata, "threshold")
        input_dim = int(
            metadata.get("input_dim", window_size * len(feature_names))
        )
        expected_input_dim = window_size * len(feature_names)
        if input_dim != expected_input_dim:
            raise ModelArtifactError(
                "Autoencoder artifact input_dim does not match window_size "
                "and feature_names."
            )
        latent_dim = _required_positive_int(metadata, "latent_dim")
        model, scaler = _load_autoencoder_runtime(
            artifact_path=artifact_path,
            input_dim=input_dim,
            latent_dim=latent_dim,
        )

        return AutoencoderArtifactScoringModel(
            threshold=threshold,
            metadata=metadata,
            model=model,
            scaler=scaler,
            feature_names=feature_names,
            window_size=window_size,
            feature_statistics=feature_statistics_from_metadata(
                feature_names,
                metadata,
                scaler,
            ),
        )

    def _load_legacy_directory(self, artifact_path: Path) -> ModelArtifact:
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


def _load_autoencoder_runtime(
    artifact_path: Path,
    input_dim: int,
    latent_dim: int,
) -> tuple[Any, Any]:
    try:
        import joblib
    except ImportError as exc:
        raise ModelArtifactError(
            "Autoencoder artifact loading requires joblib."
        ) from exc

    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise ModelArtifactError(
            "Autoencoder artifact loading requires PyTorch."
        ) from exc

    class AutoencoderNetwork(nn.Module):
        def __init__(self, input_dim: int, latent_dim: int) -> None:
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, 256),
                nn.ReLU(),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Linear(128, latent_dim),
            )
            self.decoder = nn.Sequential(
                nn.Linear(latent_dim, 128),
                nn.ReLU(),
                nn.Linear(128, 256),
                nn.ReLU(),
                nn.Linear(256, input_dim),
            )

        def forward(self, value):
            encoded = self.encoder(value)
            return self.decoder(encoded)

    try:
        scaler = joblib.load(artifact_path / "scaler.joblib")
        model = AutoencoderNetwork(input_dim=input_dim, latent_dim=latent_dim)
        try:
            state_dict = torch.load(
                artifact_path / "model.pt",
                map_location="cpu",
                weights_only=True,
            )
        except TypeError:
            state_dict = torch.load(artifact_path / "model.pt", map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()
    except ModuleNotFoundError as exc:
        raise ModelArtifactError(
            "Autoencoder artifact loading requires PyTorch and joblib."
        ) from exc
    except Exception as exc:
        raise ModelArtifactError(
            "Autoencoder artifact files could not be loaded."
        ) from exc

    return model, scaler


def _required_str_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ModelArtifactError(
            f"Artifact metadata field `{key}` must be a non-empty string array."
        )
    return tuple(value)


def _required_positive_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ModelArtifactError(
            f"Artifact metadata field `{key}` must be a positive integer."
        )
    return value


def _required_number(payload: Mapping[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise ModelArtifactError(f"Artifact field `{key}` must be numeric.")
    return float(value)


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
