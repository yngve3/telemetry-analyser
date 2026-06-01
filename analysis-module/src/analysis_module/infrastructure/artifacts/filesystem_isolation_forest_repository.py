"""Filesystem repository for trained Isolation Forest artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis_module.application.reason_diagnostics import (
    feature_statistics_from_metadata,
)
from analysis_module.detectors.model_based.isolation_forest import (
    IsolationForestArtifactModel,
)
from analysis_module.detectors.model_based.model_artifact import ModelArtifactError


@dataclass(frozen=True, slots=True)
class FilesystemIsolationForestArtifactRepository:
    """Loads a trained sklearn Isolation Forest artifact from a directory."""

    def load(self, path: str | Path) -> IsolationForestArtifactModel:
        artifact_path = Path(path)
        if not artifact_path.is_dir():
            raise ModelArtifactError(
                "Isolation Forest artifact path must be a directory."
            )

        for file_name in ("model.joblib", "scaler.joblib", "metadata.json"):
            if not (artifact_path / file_name).is_file():
                raise ModelArtifactError(
                    f"Isolation Forest artifact is missing required file `{file_name}`."
                )

        metadata = _read_json_file(artifact_path / "metadata.json")
        if metadata.get("model_type") != "isolation_forest":
            raise ModelArtifactError(
                "Isolation Forest artifact metadata has an invalid model_type."
            )

        feature_names = metadata.get("feature_names")
        if not isinstance(feature_names, list) or not all(
            isinstance(name, str) for name in feature_names
        ):
            raise ModelArtifactError(
                "Isolation Forest artifact metadata must contain feature_names."
            )

        threshold = metadata.get("threshold")
        if not isinstance(threshold, int | float):
            raise ModelArtifactError(
                "Isolation Forest artifact metadata must contain a numeric threshold."
            )

        window_size = metadata.get("window_size")
        if not isinstance(window_size, int) or window_size <= 0:
            raise ModelArtifactError(
                "Isolation Forest artifact metadata must contain a positive window_size."
            )

        model, scaler = _load_joblib_artifacts(artifact_path)
        return IsolationForestArtifactModel(
            model=model,
            scaler=scaler,
            feature_names=tuple(feature_names),
            threshold=float(threshold),
            window_size=window_size,
            metadata=metadata,
            feature_statistics=feature_statistics_from_metadata(
                feature_names,
                metadata,
                scaler,
            ),
        )


def _load_joblib_artifacts(artifact_path: Path) -> tuple[Any, Any]:
    try:
        import joblib
    except ImportError as exc:
        raise ModelArtifactError(
            "Isolation Forest artifact loading requires joblib and scikit-learn."
        ) from exc

    try:
        return (
            joblib.load(artifact_path / "model.joblib"),
            joblib.load(artifact_path / "scaler.joblib"),
        )
    except ModuleNotFoundError as exc:
        raise ModelArtifactError(
            "Isolation Forest artifact loading requires joblib and scikit-learn."
        ) from exc


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise ModelArtifactError(
            f"Isolation Forest artifact file `{path.name}` is not valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise ModelArtifactError(
            f"Isolation Forest artifact file `{path.name}` must contain an object."
        )
    return payload
