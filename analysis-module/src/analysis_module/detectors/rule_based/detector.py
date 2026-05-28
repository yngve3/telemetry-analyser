"""Detector adapter for deterministic telemetry rules."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from analysis_module.application.context import AnalysisContext
from analysis_module.detectors.rule_based.default_rules import create_default_rules
from analysis_module.domain import (
    DetectedAnomaly,
    DetectorKind,
    DetectorOutput,
    TelemetryRule,
)


@dataclass(frozen=True, slots=True)
class RuleBasedDetector:
    """Runs registered deterministic rules against a read-only context."""

    rules: Sequence[TelemetryRule] = field(default_factory=create_default_rules)
    name: str = "rule_based"
    kind: DetectorKind = DetectorKind.RULE_BASED

    def analyze(self, context: AnalysisContext) -> DetectorOutput:
        anomalies: list[DetectedAnomaly] = []
        for rule in self.rules:
            anomaly = rule.evaluate(context.current, context.history)
            if anomaly is not None:
                anomalies.append(anomaly)

        return DetectorOutput(
            detector_name=self.name,
            detector_kind=self.kind,
            anomalies=tuple(anomalies),
        )
