"""Synthetic mission initial state."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InitialState:
    """Initial UAV state for mission playback."""

    latitude: float
    longitude: float
    altitude: float
    battery: float
    heading_deg: float = 0.0
