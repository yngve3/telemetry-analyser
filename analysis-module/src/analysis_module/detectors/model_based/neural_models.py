"""Placeholders for neural telemetry scoring models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from analysis_module.detectors.model_based._windowing import normalized_rmse
from analysis_module.detectors.model_based.interfaces import ModelScore
from analysis_module.features.feature_window import FeatureWindow


@dataclass(frozen=True, slots=True)
class AutoencoderArtifactScoringModel:
    """Artifact-backed scoring contract for future autoencoder inference."""

    threshold: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def score(self, feature_window: FeatureWindow) -> ModelScore:
        matrix = feature_window.values_matrix()
        if len(matrix) < 2:
            return ModelScore(
                score=0.0,
                threshold=self.threshold,
                confidence=0.0,
                metadata=self.metadata,
            )

        reconstruction_error = normalized_rmse(matrix[:-1], matrix[-1])
        confidence = 0.0
        if reconstruction_error > self.threshold:
            confidence = min(
                1.0,
                0.5
                + (reconstruction_error - self.threshold)
                / max(self.threshold * 2.0, 1e-9),
            )

        return ModelScore(
            score=reconstruction_error,
            threshold=self.threshold,
            confidence=confidence,
            metadata=self.metadata,
        )
