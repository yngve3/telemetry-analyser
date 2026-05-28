"""Snapshot source configuration."""

from dataclasses import dataclass

from telemetry_source_backend.domain.snapshot.models.snapshot_playback_mode import (
    SnapshotPlaybackMode,
)


@dataclass(frozen=True, slots=True)
class SnapshotConfig:
    """Configuration for snapshot sending or playback."""

    name: str
    playback_mode: SnapshotPlaybackMode = SnapshotPlaybackMode.SEND_ONCE
    repeat: bool = False
    interval_seconds: float = 1.0
