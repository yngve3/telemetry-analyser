"""Neural telemetry scoring models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from analysis_module.application.reason_diagnostics import (
    FeatureStatistics,
    ReasonDiagnostics,
)
from analysis_module.detectors.model_based._windowing import normalized_rmse
from analysis_module.detectors.model_based.interfaces import ModelScore
from analysis_module.domain import UnifiedTelemetry
from analysis_module.features.model_features import (
    extract_sequence_diagnostic_values,
    extract_sequence_feature_values,
)
from analysis_module.features.feature_window import FeatureWindow


@dataclass(frozen=True, slots=True)
class AutoencoderArtifactScoringModel:
    """Artifact-backed autoencoder scoring model."""

    threshold: float
    metadata: Mapping[str, Any] = field(default_factory=dict)
    model: Any | None = None
    scaler: Any | None = None
    feature_names: tuple[str, ...] = ()
    window_size: int = 0
    feature_statistics: Mapping[str, FeatureStatistics] = field(default_factory=dict)
    reason_diagnostics: ReasonDiagnostics = field(default_factory=ReasonDiagnostics)

    @property
    def is_ready(self) -> bool:
        return (
            self.model is not None
            and self.scaler is not None
            and bool(self.feature_names)
            and self.window_size > 0
        )

    def score_samples(self, samples: Sequence[UnifiedTelemetry]) -> ModelScore:
        if not self.is_ready:
            return ModelScore(
                score=0.0,
                threshold=self.threshold,
                confidence=0.0,
                metadata=self.metadata,
            )

        window_samples = tuple(samples[-self.window_size :])
        if len(window_samples) < self.window_size:
            return ModelScore(
                score=0.0,
                threshold=self.threshold,
                confidence=0.0,
                metadata=self.metadata,
            )

        torch = _import_torch()
        row = [list(extract_sequence_feature_values(window_samples, self.feature_names))]
        scaled_row = self.scaler.transform(row)
        tensor = torch.tensor(scaled_row, dtype=torch.float32)

        self.model.eval()
        with torch.no_grad():
            restored = self.model(tensor)
            errors = torch.mean((tensor - restored) ** 2, dim=1)
            reconstruction_error = float(errors[0].item())

        diagnostics = self.reason_diagnostics.diagnose(
            extract_sequence_diagnostic_values(window_samples, self.feature_names),
            self.feature_statistics,
        )
        return ModelScore(
            score=reconstruction_error,
            threshold=self.threshold,
            confidence=_confidence(reconstruction_error, self.threshold),
            metadata=self.metadata,
            feature_scores=diagnostics.feature_scores,
            reasons=diagnostics.reasons,
        )

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
        return ModelScore(
            score=reconstruction_error,
            threshold=self.threshold,
            confidence=_confidence(reconstruction_error, self.threshold),
            metadata=self.metadata,
        )


def _confidence(score: float, threshold: float) -> float:
    if score <= threshold:
        return 0.0
    return min(
        1.0,
        0.5 + (score - threshold) / max(threshold * 2.0, 1e-9),
    )


def _import_torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Autoencoder inference requires PyTorch.") from exc
    return torch
