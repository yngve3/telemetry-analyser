"""Aggregates detector output into a public analysis result."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from analysis_module.application.cause_diagnosis import CauseDiagnosisLayer

from analysis_module.domain import (
    AnomalySource,
    AnomalyResult,
    AnomalyType,
    DetectedAnomaly,
    DetectorOutput,
    Severity,
    UnifiedTelemetry,
)

_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.CRITICAL: 2,
}


@dataclass(frozen=True, slots=True)
class ResultAggregator:
    """Builds source-aware `AnomalyResult` objects from detector output."""

    cause_diagnosis: CauseDiagnosisLayer = field(
        default_factory=CauseDiagnosisLayer
    )

    def aggregate(
        self,
        telemetry: UnifiedTelemetry,
        anomalies: Iterable[DetectedAnomaly],
    ) -> AnomalyResult:
        output = DetectorOutput(
            detector_name="aggregated",
            detector_kind=_detector_kind_for_legacy_anomalies(),
            anomalies=tuple(anomalies),
        )
        return self.aggregate_outputs(telemetry, (output,))

    def aggregate_outputs(
        self,
        telemetry: UnifiedTelemetry,
        outputs: Iterable[DetectorOutput],
    ) -> AnomalyResult:
        detector_outputs = tuple(outputs)
        return AnomalyResult(
            drone_id=telemetry.drone_id,
            telemetry_timestamp=telemetry.timestamp,
            anomalies=self._aggregate_anomalies(detector_outputs),
            detector_outputs=detector_outputs,
        )

    def _aggregate_anomalies(
        self,
        outputs: tuple[DetectorOutput, ...],
    ) -> tuple[DetectedAnomaly, ...]:
        grouped: dict[AnomalyType, list[tuple[DetectorOutput, DetectedAnomaly]]] = {}
        for output in outputs:
            for anomaly in output.anomalies:
                grouped.setdefault(anomaly.type, []).append((output, anomaly))

        anomalies = [
            self._merge_group(anomaly_type, items)
            for anomaly_type, items in grouped.items()
        ]
        return tuple(sorted(anomalies, key=_anomaly_rank, reverse=True))

    def _merge_group(
        self,
        anomaly_type: AnomalyType,
        items: list[tuple[DetectorOutput, DetectedAnomaly]],
    ) -> DetectedAnomaly:
        best = max(
            (anomaly for _, anomaly in items),
            key=lambda anomaly: (_SEVERITY_RANK[anomaly.severity], anomaly.confidence),
        )
        severity = max(
            (anomaly.severity for _, anomaly in items),
            key=lambda value: _SEVERITY_RANK[value],
        )
        confidence = max(anomaly.confidence for _, anomaly in items)
        reason_source = best
        if not reason_source.reasons:
            reason_source = next(
                (
                    anomaly
                    for _, anomaly in items
                    if anomaly.reasons
                ),
                best,
            )
        sources = tuple(
            AnomalySource(
                detector=output.detector_name,
                confidence=anomaly.confidence,
                evidence=anomaly.evidence,
                severity=anomaly.severity,
                message=anomaly.message,
            )
            for output, anomaly in items
        )

        merged = DetectedAnomaly(
            type=anomaly_type,
            severity=severity,
            message=best.message,
            confidence=confidence,
            source=best.source,
            detector_kind=best.detector_kind,
            detector_name=best.detector_name,
            model_name=best.model_name,
            score=best.score,
            affected_fields=best.affected_fields,
            affected_parameters=best.affected_parameters,
            evidence=best.evidence,
            window_start=best.window_start,
            window_end=best.window_end,
            probable_cause=best.probable_cause,
            cause_confidence=best.cause_confidence,
            diagnostic_evidence=best.diagnostic_evidence,
            reasons=reason_source.reasons,
            recommended_action=best.recommended_action,
            sources=sources,
        )
        return self.cause_diagnosis.enrich(merged)


def _detector_kind_for_legacy_anomalies():
    from analysis_module.domain import DetectorKind

    return DetectorKind.RULE_BASED


def _anomaly_rank(anomaly: DetectedAnomaly) -> tuple[int, float, int]:
    return (
        _SEVERITY_RANK[anomaly.severity],
        anomaly.confidence,
        len(anomaly.sources),
    )
