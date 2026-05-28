"""Synthetic mission phase."""

from dataclasses import dataclass

from telemetry_source_backend.domain.synthetic.models.phase_type import PhaseType


@dataclass(frozen=True, slots=True)
class MissionPhase:
    """One time-bounded mission phase."""

    type: PhaseType
    duration_sec: float
    target_altitude: float | None = None
    target_latitude: float | None = None
    target_longitude: float | None = None
    target_speed: float | None = None
    target_heading_deg: float | None = None
