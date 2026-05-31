"""Domain models for anomaly analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from analysis_module.domain.detectors import DetectorOutput


EvidenceValue: TypeAlias = str | int | float | bool | None


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
class DetectedAnomaly:
    """Single anomaly detected for a telemetry sample."""

    type: AnomalyType
    severity: Severity
    message: str
    confidence: float = 1.0
    source: str = "rule_based"
    detector_name: str = "unknown"
    affected_fields: tuple[str, ...] = ()
    evidence: dict[str, EvidenceValue] = field(default_factory=dict)
    sources: tuple[AnomalySource, ...] = ()

    def to_dict(self, include_sources: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "confidence": self.confidence,
            "source": self.source,
            "detector_name": self.detector_name,
            "affected_fields": list(self.affected_fields),
            "evidence": self.evidence,
        }
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

    @property
    def has_anomalies(self) -> bool:
        return bool(self.anomalies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drone_id": self.drone_id,
            "telemetry_timestamp": self.telemetry_timestamp.isoformat(),
            "has_anomalies": self.has_anomalies,
            "anomalies": [
                anomaly.to_dict(include_sources=True)
                for anomaly in self.anomalies
            ],
            "detector_outputs": {
                output.detector_name: output.to_dict()
                for output in self.detector_outputs
            },
        }


AnalysisResult: TypeAlias = AnomalyResult
PipelineAnalysisResult: TypeAlias = AnomalyResult
