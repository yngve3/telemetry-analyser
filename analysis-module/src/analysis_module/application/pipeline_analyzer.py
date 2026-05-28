"""Stateful analyzer that runs detector-level implementations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from analysis_module.application.context import AnalysisContext
from analysis_module.application.detector import TelemetryDetector
from analysis_module.application.result_aggregator import ResultAggregator
from analysis_module.domain import AnomalyResult, DetectorOutput, UnifiedTelemetry
from analysis_module.features.feature_extractor import TelemetryFeatureExtractor
from analysis_module.features.telemetry_history import TelemetryHistory


@dataclass(slots=True)
class DetectorPipelineAnalyzer:
    """Analyzer that updates history once and runs enabled detectors."""

    detectors: Sequence[TelemetryDetector]
    history: TelemetryHistory = field(default_factory=TelemetryHistory)
    result_aggregator: ResultAggregator = field(default_factory=ResultAggregator)
    feature_extractor: TelemetryFeatureExtractor = field(
        default_factory=TelemetryFeatureExtractor
    )
    feature_window_size: int | None = None

    def analyze_next(self, telemetry: UnifiedTelemetry) -> AnomalyResult:
        outputs = self.analyze_next_with_outputs(telemetry)
        return self.result_aggregator.aggregate_outputs(telemetry, outputs)

    def analyze_next_with_outputs(
        self,
        telemetry: UnifiedTelemetry,
    ) -> tuple[DetectorOutput, ...]:
        context = self._build_context(telemetry)
        outputs = tuple(detector.analyze(context) for detector in self.detectors)
        self.history.append(telemetry)
        return outputs

    def analyze(self, telemetry: UnifiedTelemetry) -> AnomalyResult:
        """Backward-compatible alias for older callers."""

        return self.analyze_next(telemetry)

    def _build_context(self, telemetry: UnifiedTelemetry) -> AnalysisContext:
        feature_window = None
        if self.feature_window_size is not None:
            samples = (*self.history.samples(), telemetry)
            feature_window = self.feature_extractor.extract_window(
                samples[-self.feature_window_size :]
            )
        return AnalysisContext(
            current=telemetry,
            history=self.history,
            feature_window=feature_window,
        )
