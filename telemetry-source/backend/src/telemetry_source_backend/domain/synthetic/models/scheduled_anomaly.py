"""Scheduled synthetic anomaly."""

from dataclasses import dataclass

from telemetry_source_backend.domain.synthetic.models.anomaly_profile import (
    AnomalyProfile,
)


@dataclass(frozen=True, slots=True)
class ScheduledAnomaly:
    """An anomaly activated for a bounded interval during mission playback."""

    profile: AnomalyProfile
    start_sec: float
    duration_sec: float

    def is_active_at(self, elapsed_sec: float) -> bool:
        return self.start_sec <= elapsed_sec < self.start_sec + self.duration_sec
