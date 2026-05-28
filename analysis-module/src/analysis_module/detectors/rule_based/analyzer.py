"""Rule-based telemetry analyzer."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from analysis_module.application.context import AnalysisContext
from analysis_module.application.result_aggregator import ResultAggregator
from analysis_module.detectors.rule_based.default_rules import create_default_rules
from analysis_module.detectors.rule_based.detector import RuleBasedDetector
from analysis_module.domain import AnomalyResult, TelemetryRule
from analysis_module.domain.models import UnifiedTelemetry
from analysis_module.features.telemetry_history import TelemetryHistory


@dataclass(slots=True)
class RuleBasedTelemetryAnalyzer:
    """Analyzer that evaluates deterministic rules with bounded history."""

    rules: Sequence[TelemetryRule] = field(default_factory=create_default_rules)
    history: TelemetryHistory = field(default_factory=TelemetryHistory)
    result_aggregator: ResultAggregator = field(default_factory=ResultAggregator)

    def analyze_next(self, telemetry: UnifiedTelemetry) -> AnomalyResult:
        output = RuleBasedDetector(rules=self.rules).analyze(
            AnalysisContext(
                current=telemetry,
                history=self.history,
            )
        )
        self.history.append(telemetry)
        return self.result_aggregator.aggregate_outputs(telemetry, (output,))

    def analyze(self, telemetry: UnifiedTelemetry) -> AnomalyResult:
        """Backward-compatible alias for older callers."""

        return self.analyze_next(telemetry)
