"""Synthetic mission motion profile."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MotionProfile:
    """Simple movement limits used by mission compilation and playback."""

    horizontal_acceleration_m_s2: float = 2.0
    default_climb_rate_m_s: float = 3.0
    default_descent_rate_m_s: float = 2.0
    default_yaw_rate_deg_s: float = 45.0
    default_return_speed_m_s: float = 8.0

