"""Bounded telemetry history for stateful analysis."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from analysis_module.domain.models import UnifiedTelemetry


@dataclass(slots=True)
class TelemetryHistory:
    """Stores a bounded sequence of telemetry samples."""

    max_size: int = 1_000
    _samples: deque[UnifiedTelemetry] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_size <= 0:
            raise ValueError("TelemetryHistory max_size must be positive.")
        self._samples = deque(maxlen=self.max_size)

    def append(self, telemetry: UnifiedTelemetry) -> None:
        self._samples.append(telemetry)

    def extend(self, samples: Iterable[UnifiedTelemetry]) -> None:
        for sample in samples:
            self.append(sample)

    def previous(self) -> UnifiedTelemetry | None:
        if not self._samples:
            return None
        return self._samples[-1]

    def recent(
        self,
        seconds: float,
        current_time: datetime | None = None,
    ) -> tuple[UnifiedTelemetry, ...]:
        if seconds < 0:
            raise ValueError("Window size in seconds must not be negative.")
        if not self._samples:
            return ()

        end_time = current_time or self._samples[-1].timestamp
        start_time = end_time - timedelta(seconds=seconds)
        return tuple(
            sample
            for sample in self._samples
            if start_time <= sample.timestamp <= end_time
        )

    def samples(self) -> tuple[UnifiedTelemetry, ...]:
        return tuple(self._samples)

    def __len__(self) -> int:
        return len(self._samples)
