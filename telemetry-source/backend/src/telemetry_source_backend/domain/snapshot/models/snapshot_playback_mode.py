"""Snapshot playback mode."""

from enum import StrEnum


class SnapshotPlaybackMode(StrEnum):
    """Supported snapshot playback modes."""

    SEND_ONCE = "send_once"
    STREAM = "stream"

