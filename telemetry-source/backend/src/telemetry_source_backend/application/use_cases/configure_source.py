"""Use case for configuring a telemetry source."""

from dataclasses import dataclass

from telemetry_source_backend.application.ports import SourceRepository
from telemetry_source_backend.domain.common.models import SourceProfile


@dataclass(frozen=True, slots=True)
class ConfigureSource:
    repository: SourceRepository

    async def execute(self, profile: SourceProfile) -> None:
        await self.repository.save(profile)
