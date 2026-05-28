"""Snapshot telemetry model."""

from dataclasses import dataclass

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.snapshot.models.snapshot_config import SnapshotConfig


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Uploaded telemetry snapshot owned by the snapshot source mode."""

    snapshot_id: str
    config: SnapshotConfig
    samples: tuple[TelemetrySample, ...]
