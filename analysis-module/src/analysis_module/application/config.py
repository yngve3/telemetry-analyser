"""Configuration for telemetry analyzers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class AnalyzerConfig:
    """Configuration used by analyzer factories."""

    history_size: int = 1_000
    enabled_detectors: tuple[str, ...] = ("rule_based",)
    enabled_rules: tuple[str, ...] | None = None
    thresholds: Mapping[str, float] = field(default_factory=dict)
    model_artifact_path: str | Path | None = None
    adaptive_correlation_profile_path: str | Path | None = None
    isolation_forest_artifact_path: str | Path | None = None
    model_window_size: int = 50
