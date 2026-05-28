"""Synthetic mission phase type."""

from enum import StrEnum


class PhaseType(StrEnum):
    """Supported mission phase types."""

    TAKEOFF = "takeoff"
    WAYPOINT = "waypoint"
    TURN = "turn"
    HOVER = "hover"
    RETURN_HOME = "return_home"
    LANDING = "landing"
