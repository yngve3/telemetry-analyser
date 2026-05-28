"""Synthetic battery drain profile."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BatteryProfile:
    """Phase-based battery drain rates in percent per second."""

    takeoff_percent_per_sec: float = 0.025
    waypoint_percent_per_sec: float = 0.015
    turn_percent_per_sec: float = 0.010
    hover_percent_per_sec: float = 0.012
    return_home_percent_per_sec: float = 0.015
    landing_percent_per_sec: float = 0.010

