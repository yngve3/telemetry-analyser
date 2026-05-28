"""In-memory registry for synthetic mission runners."""

from dataclasses import dataclass

from telemetry_source_backend.domain.synthetic.models import MissionPlan
from telemetry_source_backend.domain.synthetic.script.models import MissionScript
from telemetry_source_backend.domain.synthetic.services.mission_runner import (
    MissionRunner,
)


@dataclass(slots=True)
class SyntheticMissionRecord:
    """Stored synthetic mission runtime."""

    mission_id: str
    script: MissionScript
    plan: MissionPlan
    runner: MissionRunner


class InMemorySyntheticMissionRegistry:
    """Stores synthetic mission runners for the backend process lifetime."""

    def __init__(self) -> None:
        self._records: dict[str, SyntheticMissionRecord] = {}

    def save(self, record: SyntheticMissionRecord) -> None:
        self._records[record.mission_id] = record

    def get(self, mission_id: str) -> SyntheticMissionRecord | None:
        return self._records.get(mission_id)

    def list(self) -> list[SyntheticMissionRecord]:
        return list(self._records.values())

