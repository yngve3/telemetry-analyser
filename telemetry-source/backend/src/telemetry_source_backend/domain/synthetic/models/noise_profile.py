"""Synthetic telemetry noise profile."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoiseProfile:
    """Deterministic sensor noise configuration."""

    random_seed: int | None = None
    gps_position_std_m: float = 0.0
    altitude_std_m: float = 0.0
    speed_std_m_s: float = 0.0
    heading_std_deg: float = 0.0
    battery_std_percent: float = 0.0

