"""Synthetic mission runtime command."""

from dataclasses import dataclass, field
from typing import Any, Mapping

from telemetry_source_backend.domain.synthetic.models.command_type import CommandType


@dataclass(frozen=True, slots=True)
class MissionCommand:
    """Command submitted to a running synthetic mission."""

    command: CommandType
    parameters: Mapping[str, Any] = field(default_factory=dict)

