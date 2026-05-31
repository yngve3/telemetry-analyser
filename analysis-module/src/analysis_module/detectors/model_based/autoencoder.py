"""Autoencoder-style reconstruction detector."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from analysis_module.application.context import AnalysisContext
from analysis_module.detectors.model_based._windowing import (
    normalized_rmse,
    resolve_feature_window,
    top_feature_deviations,
)
from analysis_module.detectors.model_based.interfaces import TelemetryScoringModel
from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    DetectorKind,
    DetectorOutput,
    Severity,
)
from analysis_module.features.feature_extractor import TelemetryFeatureExtractor
from analysis_module.features.feature_window import FeatureWindow


@dataclass(frozen=True, slots=True)
class AutoencoderDetector:
    """Detects reconstruction-error anomalies from a telemetry feature window."""

    name: str = "autoencoder"
    kind: DetectorKind = DetectorKind.MODEL_BASED
    model_name: str = "autoencoder_reconstruction_baseline_v1"
    window_size: int = 50
    min_window_size: int = 5
    reconstruction_error_threshold: float = 3.0
    scoring_model: TelemetryScoringModel | None = None
    feature_extractor: TelemetryFeatureExtractor = field(
        default_factory=TelemetryFeatureExtractor
    )

    def analyze(self, context: AnalysisContext) -> DetectorOutput:
        resolved = resolve_feature_window(
            context,
            window_size=self.window_size,
            feature_extractor=self.feature_extractor,
        )
        if resolved is None or len(resolved.feature_window) < self.min_window_size:
            return self._empty_output()

        matrix = resolved.feature_window.values_matrix()
        reference_rows = matrix[:-1]
        current_row = matrix[-1]
        if not reference_rows:
            return self._empty_output()

        score, threshold, confidence, score_metadata = self._score_window(
            resolved.feature_window,
            reference_rows,
            current_row,
        )
        if score <= threshold:
            return self._empty_output()

        affected_parameters, top_errors = top_feature_deviations(
            resolved.feature_window.feature_names,
            reference_rows,
            current_row,
        )
        evidence: dict[str, Any] = {
            "reconstruction_error": score,
            "threshold": threshold,
            "window_size": len(resolved.feature_window),
            "top_feature_errors": top_errors,
        }
        if score_metadata:
            evidence["model_metadata"] = dict(score_metadata)

        anomaly = DetectedAnomaly(
            type=AnomalyType.ANOMALOUS_BEHAVIOR,
            severity=(
                Severity.CRITICAL
                if threshold > 0.0 and score >= threshold * 2.0
                else Severity.WARNING
            ),
            message="Feature reconstruction error exceeded the anomaly threshold.",
            confidence=confidence,
            source=self.kind.value,
            detector_kind=self.kind.value,
            detector_name=self.name,
            model_name=_model_name(self.model_name, score_metadata),
            score=score,
            affected_parameters=affected_parameters,
            evidence=evidence,
            window_start=resolved.samples[0].timestamp,
            window_end=resolved.samples[-1].timestamp,
            probable_cause=(
                "The latest feature vector is poorly reconstructed from recent "
                "normal telemetry dynamics."
            ),
        )
        return DetectorOutput(
            detector_name=self.name,
            detector_kind=self.kind,
            anomalies=(anomaly,),
        )

    def _score_window(
        self,
        feature_window: FeatureWindow,
        reference_rows: Sequence[Sequence[float]],
        current_row: Sequence[float],
    ) -> tuple[float, float, float, dict[str, Any]]:
        if self.scoring_model is not None:
            model_score = self.scoring_model.score(feature_window)
            return (
                model_score.score,
                model_score.threshold,
                model_score.confidence,
                dict(model_score.metadata),
            )

        reconstruction_error = normalized_rmse(reference_rows, current_row)
        confidence = min(
            1.0,
            0.5
            + (reconstruction_error - self.reconstruction_error_threshold)
            / max(self.reconstruction_error_threshold * 2.0, 1e-9),
        )
        return (
            reconstruction_error,
            self.reconstruction_error_threshold,
            confidence,
            {},
        )

    def _empty_output(self) -> DetectorOutput:
        return DetectorOutput(detector_name=self.name, detector_kind=self.kind)


def _model_name(default: str, metadata: dict[str, Any]) -> str:
    model_type = metadata.get("model_type")
    feature_version = metadata.get("feature_version")
    if isinstance(model_type, str) and isinstance(feature_version, str):
        return f"{model_type}:{feature_version}"
    if isinstance(model_type, str):
        return model_type
    return default
