"""In-memory registry for uploaded telemetry snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from telemetry_source_backend.domain.snapshot.models import Snapshot


@dataclass(slots=True)
class SnapshotRecord:
    """Stored telemetry snapshot."""

    snapshot: Snapshot
    snapshot_id: str = field(default_factory=lambda: str(uuid4()))


class InMemorySnapshotRegistry:
    """Stores uploaded snapshots for the backend process lifetime."""

    def __init__(self) -> None:
        self._records: dict[str, SnapshotRecord] = {}

    def save(self, record: SnapshotRecord) -> None:
        self._records[record.snapshot_id] = record

    def get(self, snapshot_id: str) -> SnapshotRecord | None:
        return self._records.get(snapshot_id)

    def list(self) -> list[SnapshotRecord]:
        return list(self._records.values())
