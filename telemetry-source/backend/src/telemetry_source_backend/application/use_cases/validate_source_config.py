"""Use case for validating source configuration."""

from telemetry_source_backend.domain.common.models import SourceProfile


class ValidateSourceConfig:
    def execute(self, profile: SourceProfile) -> None:
        raise NotImplementedError
