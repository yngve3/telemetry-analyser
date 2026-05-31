"""Detector that adapts a scoring model to anomaly results."""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis_module.application.context import AnalysisContext
from analysis_module.detectors.model_based.interfaces import TelemetryScoringModel
from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    DetectorKind,
    DetectorOutput,
    Severity,
    UnifiedTelemetry,
)
from analysis_module.features.feature_extractor import TelemetryFeatureExtractor
from analysis_module.features.telemetry_history import TelemetryHistory


@dataclass(frozen=True, slots=True)
class ScoringDetector:
    """Runs a scoring model against the latest feature window."""

    model: TelemetryScoringModel
    window_size: int = 50
    name: str = "model_based"
    kind: DetectorKind = DetectorKind.ML
    anomaly_type: AnomalyType = AnomalyType.ANOMALOUS_BEHAVIOR
    feature_extractor: TelemetryFeatureExtractor = field(
        default_factory=TelemetryFeatureExtractor
    )

    def analyze(self, context: AnalysisContext) -> DetectorOutput:
        feature_window = context.feature_window
        if feature_window is None or len(feature_window) < self.window_size:
            samples = (*context.history.samples(), context.current)
            if len(samples) < self.window_size:
                return self._empty_output()
            feature_window = self.feature_extractor.extract_window(
                samples[-self.window_size :]
            )

        score = self.model.score(feature_window)
        if score.score <= score.threshold:
            return self._empty_output()

        severity = (
            Severity.CRITICAL
            if score.threshold > 0.0 and score.score > score.threshold * 2.0
            else Severity.WARNING
        )
        return DetectorOutput(
            detector_name=self.name,
            detector_kind=self.kind,
            anomalies=(
                DetectedAnomaly(
                    type=self.anomaly_type,
                    severity=severity,
                    message="Model score exceeded the configured anomaly threshold.",
                    confidence=score.confidence,
                    source=self.kind.value,
                    detector_name=self.name,
                    affected_fields=("feature_window",),
                    evidence={
                        "score": score.score,
                        "threshold": score.threshold,
                        "window_size": self.window_size,
                    },
                ),
            ),
        )

    def evaluate(
        self,
        current: UnifiedTelemetry,
        history: TelemetryHistory,
    ) -> DetectedAnomaly | None:
        output = self.analyze(
            AnalysisContext(
                current=current,
                history=history,
            )
        )
        if not output.anomalies:
            return None
        return output.anomalies[0]

    def _empty_output(self) -> DetectorOutput:
        return DetectorOutput(
            detector_name=self.name,
            detector_kind=self.kind,
        )
