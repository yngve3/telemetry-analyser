"""Synthetic anomaly profile."""

from dataclasses import dataclass

from telemetry_source_backend.domain.synthetic.models.anomaly_type import AnomalyType


@dataclass(frozen=True, slots=True)
class AnomalyProfile:
    """Configuration for synthetic anomaly injection."""

    anomaly_type: AnomalyType
    intensity: float

