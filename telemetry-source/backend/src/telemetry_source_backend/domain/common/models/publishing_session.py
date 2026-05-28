"""Publishing session domain model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublishingSession:
    """Represents an active telemetry publishing session."""

    id: str
    source_profile_id: str
    encoder: str
    transport: str
    is_active: bool

