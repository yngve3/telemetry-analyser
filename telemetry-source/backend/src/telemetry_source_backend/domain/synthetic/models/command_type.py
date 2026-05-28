"""Synthetic mission command type."""

from enum import StrEnum


class CommandType(StrEnum):
    """Commands accepted by the synthetic mission runtime."""

    INJECT_ANOMALY = "inject_anomaly"
    SET_PARAMETER = "set_parameter"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"

