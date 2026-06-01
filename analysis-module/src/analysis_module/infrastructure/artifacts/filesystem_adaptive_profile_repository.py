"""Filesystem repository for adaptive correlation profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis_module.detectors.model_based import AdaptiveCorrelationProfile
from analysis_module.detectors.model_based.model_artifact import ModelArtifactError


@dataclass(frozen=True, slots=True)
class FilesystemAdaptiveCorrelationProfileRepository:
    """Loads an adaptive correlation profile from a JSON file."""

    def load(self, path: str | Path) -> AdaptiveCorrelationProfile:
        profile_path = Path(path)
        if not profile_path.is_file():
            raise ModelArtifactError(
                "Adaptive correlation profile path must be a JSON file."
            )

        payload = _read_json_file(profile_path)
        try:
            return AdaptiveCorrelationProfile.from_dict(payload)
        except (TypeError, ValueError) as exc:
            raise ModelArtifactError(
                f"Adaptive correlation profile `{profile_path.name}` is invalid: {exc}"
            ) from exc


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise ModelArtifactError(
            f"Adaptive correlation profile `{path.name}` is not valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise ModelArtifactError(
            f"Adaptive correlation profile `{path.name}` must contain an object."
        )
    return payload
