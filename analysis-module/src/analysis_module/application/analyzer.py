"""Analyzer interface."""

from typing import Protocol

from analysis_module.domain import AnomalyResult, UnifiedTelemetry


class TelemetryAnalyzer(Protocol):
    """Contract for telemetry analyzers."""

    def analyze_next(self, telemetry: UnifiedTelemetry) -> AnomalyResult:
        """Analyze the next telemetry sample and return detected anomalies."""
        ...
