"""Stateful analyzer that runs detector-level implementations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from time import perf_counter

from analysis_module.application.context import AnalysisContext
from analysis_module.application.detector import (
    ProfileFeedbackDetector,
    TelemetryDetector,
)
from analysis_module.application.result_aggregator import ResultAggregator
from analysis_module.domain import (
    AnalysisTiming,
    AnomalyResult,
    DetectorOutput,
    DetectorTiming,
    UnifiedTelemetry,
)
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
        started_at = perf_counter()
        outputs = self._run_detectors(telemetry)
        result = self.result_aggregator.aggregate_outputs(telemetry, outputs)
        self._apply_profile_feedback(result)
        self.history.append(telemetry)
        return replace(
            result,
            timing=AnalysisTiming(
                total_ms=_duration_ms(started_at),
                detectors=tuple(
                    DetectorTiming(
                        detector=output.detector_name,
                        duration_ms=output.duration_ms,
                        status=output.status.value,
                    )
                    for output in outputs
                    if output.duration_ms is not None
                ),
            ),
        )

    def analyze_next_with_outputs(
        self,
        telemetry: UnifiedTelemetry,
    ) -> tuple[DetectorOutput, ...]:
        outputs = self._run_detectors(telemetry)
        self.history.append(telemetry)
        return outputs

    def analyze(self, telemetry: UnifiedTelemetry) -> AnomalyResult:
        """Backward-compatible alias for older callers."""

        return self.analyze_next(telemetry)

    def _run_detectors(
        self,
        telemetry: UnifiedTelemetry,
    ) -> tuple[DetectorOutput, ...]:
        context = self._build_context(telemetry)
        outputs: list[DetectorOutput] = []
        for detector in self.detectors:
            started_at = perf_counter()
            output = detector.analyze(context)
            outputs.append(
                replace(output, duration_ms=_duration_ms(started_at))
            )
        return tuple(outputs)

    def _apply_profile_feedback(self, result: AnomalyResult) -> None:
        for detector in self.detectors:
            if not isinstance(detector, ProfileFeedbackDetector):
                continue
            if result.has_anomalies:
                detector.discard_profile_update()
            else:
                detector.commit_profile_update()

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


def _duration_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000
