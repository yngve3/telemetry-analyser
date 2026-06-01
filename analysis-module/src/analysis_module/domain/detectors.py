"""Domain models for detector-level analysis output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from analysis_module.domain.anomalies import DetectedAnomaly


class DetectorKind(StrEnum):
    """Supported detector families."""

    RULE_BASED = "rule_based"
    MODEL_BASED = "model_based"


class DetectorStatus(StrEnum):
    """Runtime readiness status of a detector output."""

    READY = "ready"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True)
class DetectorOutput:
    """Output produced by one detector family for one telemetry sample."""

    detector_name: str
    detector_kind: DetectorKind
    anomalies: tuple[DetectedAnomaly, ...] = ()
    status: DetectorStatus = DetectorStatus.READY
    message: str | None = None
    duration_ms: float | None = None

    @property
    def has_anomalies(self) -> bool:
        return bool(self.anomalies)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "detector_name": self.detector_name,
            "detector_kind": self.detector_kind.value,
            "status": self.status.value,
            "message": self.message,
            "anomalies": [
                anomaly.to_dict(include_sources=False)
                for anomaly in self.anomalies
            ],
        }
        if self.duration_ms is not None:
            payload["duration_ms"] = self.duration_ms
        return payload
