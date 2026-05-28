"""Source repository port."""

from typing import Protocol

from telemetry_source_backend.domain.common.models import SourceProfile


class SourceRepository(Protocol):
    """Port for storing source profiles."""

    async def save(self, profile: SourceProfile) -> None:
        ...

    async def get(self, profile_id: str) -> SourceProfile | None:
        ...
