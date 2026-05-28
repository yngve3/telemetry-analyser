"""Detector contracts used by services and analyzer factories."""

from typing import Protocol

from analysis_module.application.context import AnalysisContext
from analysis_module.domain import DetectorKind, DetectorOutput


class TelemetryDetector(Protocol):
    """Detector contract for analysis-service orchestration."""

    name: str
    kind: DetectorKind

    def analyze(self, context: AnalysisContext) -> DetectorOutput:
        """Analyze one telemetry sample using a read-only context."""
        ...
