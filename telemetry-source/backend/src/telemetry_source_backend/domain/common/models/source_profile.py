"""Source profile domain model."""

from dataclasses import dataclass, field
from typing import Any, Mapping

from telemetry_source_backend.domain.common.models.source_mode import SourceMode


@dataclass(frozen=True, slots=True)
class SourceProfile:
    """Selected source mode and serialized mode-specific configuration."""

    id: str
    name: str
    mode: SourceMode
    configuration: Mapping[str, Any] = field(default_factory=dict)

