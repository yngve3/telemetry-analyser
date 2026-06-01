"""Domain models for anomaly analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from analysis_module.domain.detectors import DetectorOutput


EvidenceValue: TypeAlias = (
    str | int | float | bool | None | dict[str, Any] | tuple[Any, ...] | list[Any]
)


class Severity(StrEnum):
    """Severity of a detected anomaly."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AnomalyType(StrEnum):
    """Known anomaly categories supported by the analyzer."""

    GPS_SIGNAL_LOSS = "GPS_SIGNAL_LOSS"
    GPS_SPOOFING = "GPS_SPOOFING"
    IMU_SPIKE = "IMU_SPIKE"
    BATTERY_DROP = "BATTERY_DROP"
    LOW_BATTERY = "LOW_BATTERY"
    IMPOSSIBLE_ALTITUDE = "IMPOSSIBLE_ALTITUDE"
    TELEMETRY_FREEZE = "TELEMETRY_FREEZE"
    TELEMETRY_GAP = "TELEMETRY_GAP"
    MOTION_INCONSISTENCY = "MOTION_INCONSISTENCY"
    ANOMALOUS_BEHAVIOR = "ANOMALOUS_BEHAVIOR"


@dataclass(frozen=True, slots=True)
class AnomalyReason:
    """Post-analysis explanation for a model anomaly."""

    group: str
    score: float
    confidence: float
    features: tuple[str, ...] = ()
    feature_scores: dict[str, float] = field(default_factory=dict)
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "group": self.group,
            "score": self.score,
            "confidence": self.confidence,
            "features": list(self.features),
            "feature_scores": self.feature_scores,
        }
        if self.description is not None:
            payload["description"] = self.description
        return payload


@dataclass(frozen=True, slots=True)
class AnomalySource:
    """One detector contribution to an aggregated anomaly."""

    detector: str
    confidence: float
    evidence: dict[str, EvidenceValue] = field(default_factory=dict)
    severity: Severity | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "detector": self.detector,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }
        if self.severity is not None:
            payload["severity"] = self.severity.value
        if self.message is not None:
            payload["message"] = self.message
        return payload


@dataclass(frozen=True, slots=True)
class DetectorTiming:
    """Execution timing for one detector."""

    detector: str
    duration_ms: float
    status: str = "completed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector": self.detector,
            "duration_ms": self.duration_ms,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class AnalysisTiming:
    """Pipeline-level timing for one analysis run."""

    total_ms: float
    detectors: tuple[DetectorTiming, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ms": self.total_ms,
            "detectors": {
                timing.detector: timing.to_dict()
                for timing in self.detectors
            },
        }


@dataclass(frozen=True, slots=True)
class DetectedAnomaly:
    """Single anomaly detected for a telemetry sample."""

    type: AnomalyType
    severity: Severity
    message: str
    confidence: float = 1.0
    source: str = "rule_based"
    detector_kind: str | None = None
    detector_name: str = "unknown"
    model_name: str | None = None
    score: float | None = None
    affected_fields: tuple[str, ...] = ()
    affected_parameters: tuple[str, ...] = ()
    evidence: dict[str, EvidenceValue] = field(default_factory=dict)
    window_start: datetime | None = None
    window_end: datetime | None = None
    probable_cause: str | None = None
    cause_confidence: float | None = None
    diagnostic_evidence: dict[str, EvidenceValue] = field(default_factory=dict)
    reasons: tuple[AnomalyReason, ...] = ()
    recommended_action: str | None = None
    sources: tuple[AnomalySource, ...] = ()

    def __post_init__(self) -> None:
        if self.detector_kind is None:
            object.__setattr__(self, "detector_kind", self.source)
        if not self.affected_parameters and self.affected_fields:
            object.__setattr__(
                self,
                "affected_parameters",
                self.affected_fields,
            )
        if not self.affected_fields and self.affected_parameters:
            object.__setattr__(
                self,
                "affected_fields",
                self.affected_parameters,
            )

    def to_dict(self, include_sources: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "confidence": self.confidence,
            "source": self.source,
            "detector_kind": self.detector_kind,
            "detector_name": self.detector_name,
            "affected_fields": list(self.affected_fields),
            "affected_parameters": list(self.affected_parameters),
            "evidence": self.evidence,
            "diagnostic_evidence": self.diagnostic_evidence,
            "reasons": [reason.to_dict() for reason in self.reasons],
        }
        if self.model_name is not None:
            payload["model_name"] = self.model_name
        if self.score is not None:
            payload["score"] = self.score
        if self.window_start is not None:
            payload["window_start"] = self.window_start.isoformat()
        if self.window_end is not None:
            payload["window_end"] = self.window_end.isoformat()
        if self.probable_cause is not None:
            payload["probable_cause"] = self.probable_cause
        if self.cause_confidence is not None:
            payload["cause_confidence"] = self.cause_confidence
        if self.recommended_action is not None:
            payload["recommended_action"] = self.recommended_action
        if include_sources:
            payload["sources"] = [source.to_dict() for source in self.sources]
        return payload


@dataclass(frozen=True, slots=True)
class AnomalyResult:
    """Pipeline-level analysis result for one telemetry sample."""

    drone_id: str
    telemetry_timestamp: datetime
    anomalies: tuple[DetectedAnomaly, ...] = ()
    detector_outputs: tuple["DetectorOutput", ...] = ()
    timing: AnalysisTiming | None = None

    @property
    def has_anomalies(self) -> bool:
        return bool(self.anomalies)

    @property
    def status(self) -> str:
        if not self.anomalies:
            return "NORMAL"
        severity = _highest_severity(self.anomalies)
        if severity is Severity.CRITICAL:
            return "CRITICAL"
        if severity is Severity.WARNING:
            return "WARNING"
        return "INFO"

    @property
    def risk_level(self) -> str:
        if not self.anomalies:
            return "NONE"
        severity = _highest_severity(self.anomalies)
        if severity is Severity.CRITICAL:
            return "HIGH"
        if severity is Severity.WARNING:
            return "MEDIUM"
        return "LOW"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "drone_id": self.drone_id,
            "telemetry_timestamp": self.telemetry_timestamp.isoformat(),
            "has_anomalies": self.has_anomalies,
            "status": self.status,
            "risk_level": self.risk_level,
            "anomalies": [
                anomaly.to_dict(include_sources=True)
                for anomaly in self.anomalies
            ],
            "detector_outputs": {
                output.detector_name: output.to_dict()
                for output in self.detector_outputs
            },
        }
        if self.timing is not None:
            payload["timing"] = self.timing.to_dict()
        return payload


AnalysisResult: TypeAlias = AnomalyResult
PipelineAnalysisResult: TypeAlias = AnomalyResult


def _highest_severity(anomalies: tuple[DetectedAnomaly, ...]) -> Severity:
    severity_rank = {
        Severity.INFO: 0,
        Severity.WARNING: 1,
        Severity.CRITICAL: 2,
    }
    return max(
        (anomaly.severity for anomaly in anomalies),
        key=lambda value: severity_rank[value],
    )
