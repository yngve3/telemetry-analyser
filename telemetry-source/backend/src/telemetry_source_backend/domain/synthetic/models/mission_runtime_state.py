"""Synthetic mission runtime state."""

from dataclasses import dataclass, field
from typing import Any

from telemetry_source_backend.domain.synthetic.models.scheduled_anomaly import (
    ScheduledAnomaly,
)


@dataclass(slots=True)
class MissionRuntimeState:
    """Mutable state of a running synthetic mission."""

    mission_id: str
    elapsed_sec: float = 0.0
    active_phase_index: int = 0
    parameter_overrides: dict[str, Any] = field(default_factory=dict)
    phase_duration_overrides: dict[int, float] = field(default_factory=dict)
    phase_speed_overrides: dict[int, float] = field(default_factory=dict)
    scheduled_anomalies: list[ScheduledAnomaly] = field(default_factory=list)
    is_running: bool = False
