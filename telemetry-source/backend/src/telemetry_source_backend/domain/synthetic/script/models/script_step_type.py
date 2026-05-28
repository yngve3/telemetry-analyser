"""Human-friendly mission script step type."""

from enum import StrEnum


class ScriptStepType(StrEnum):
    """Supported mission script step types."""

    TAKEOFF = "takeoff"
    MOVE_FORWARD = "move_forward"
    TURN = "turn"
    HOVER = "hover"
    RETURN_HOME = "return_home"
    LANDING = "landing"

