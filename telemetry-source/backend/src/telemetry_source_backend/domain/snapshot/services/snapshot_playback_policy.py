"""Domain service for snapshot playback rules."""

from dataclasses import dataclass

from telemetry_source_backend.domain.snapshot.models import SnapshotConfig


@dataclass(frozen=True, slots=True)
class SnapshotPlaybackPolicy:
    """Defines how snapshot samples are emitted."""

    def should_continue(
        self,
        config: SnapshotConfig,
        emitted_count: int,
        total_samples: int,
    ) -> bool:
        if total_samples <= 0:
            return False
        if config.repeat:
            return True
        return emitted_count < total_samples
