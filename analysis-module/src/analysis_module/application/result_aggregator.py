"""Aggregates detector output into a public analysis result."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

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

        return tuple(
            self._merge_group(anomaly_type, items)
            for anomaly_type, items in grouped.items()
        )

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

        return DetectedAnomaly(
            type=anomaly_type,
            severity=severity,
            message=best.message,
            confidence=confidence,
            source=best.source,
            detector_name=best.detector_name,
            affected_fields=best.affected_fields,
            evidence=best.evidence,
            sources=sources,
        )


def _detector_kind_for_legacy_anomalies():
    from analysis_module.domain import DetectorKind

    return DetectorKind.RULE_BASED
