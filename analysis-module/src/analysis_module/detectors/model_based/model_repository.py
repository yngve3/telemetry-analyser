"""Model artifact repository contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from analysis_module.detectors.model_based.interfaces import (
    NoOpTelemetryScoringModel,
    TelemetryScoringModel,
)


class ModelArtifactRepository(Protocol):
    """Loads a telemetry scoring model from an artifact path."""

    def load(self, path: str | Path) -> TelemetryScoringModel:
        """Load a scoring model from a directory or archive."""
        ...


class NoOpModelArtifactRepository:
    """Repository stub that always returns a no-op scoring model."""

    def load(self, path: str | Path) -> TelemetryScoringModel:
        del path
        return NoOpTelemetryScoringModel()
