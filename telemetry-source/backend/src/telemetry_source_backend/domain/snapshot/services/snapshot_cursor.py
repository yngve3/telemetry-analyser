"""Snapshot playback cursor."""

from dataclasses import dataclass
from collections.abc import Sequence

from telemetry_source_backend.domain.common.models import TelemetrySample


@dataclass(slots=True)
class SnapshotCursor:
    """Tracks current position in snapshot playback."""

    samples: Sequence[TelemetrySample]
    repeat: bool = False
    index: int = 0

    def next(self) -> TelemetrySample | None:
        if not self.samples:
            return None

        if self.index >= len(self.samples):
            if not self.repeat:
                return None
            self.index = 0

        sample = self.samples[self.index]
        self.index += 1
        return sample

    def reset(self) -> None:
        self.index = 0
