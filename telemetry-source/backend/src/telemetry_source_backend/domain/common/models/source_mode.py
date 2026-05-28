"""Telemetry source mode."""

from enum import StrEnum


class SourceMode(StrEnum):
    """Supported telemetry source modes."""

    SYNTHETIC = "synthetic"
    SNAPSHOT = "snapshot"
    EXTERNAL = "external"

