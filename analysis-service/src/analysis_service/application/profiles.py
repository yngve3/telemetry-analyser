"""Analysis profile models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analysis_module import AnalyzerConfig

from analysis_service.application.model_registry import (
    detector_names_for_models,
    model_names_for_profile,
)


@dataclass(frozen=True, slots=True)
class AnalysisProfile:
    """Runtime profile used to create analysis-module analyzers."""

    model_profile: str = "rules_only"
    enabled_models: tuple[str, ...] | None = None
    enabled_rules: tuple[str, ...] | None = None
    thresholds: Mapping[str, float] = field(default_factory=dict)
    history_size: int = 1_000
    model_window_size: int = 50
    model_artifact_path: str | Path | None = None
    adaptive_correlation_profile_path: str | Path | None = None
    isolation_forest_artifact_path: str | Path | None = None

    @property
    def enabled_model_names(self) -> tuple[str, ...]:
        if self.enabled_models is not None:
            return self.enabled_models
        return model_names_for_profile(self.model_profile)

    @property
    def enabled_detector_names(self) -> tuple[str, ...]:
        return detector_names_for_models(
            self.enabled_model_names,
            require_available=True,
        )

    def to_analyzer_config(self) -> AnalyzerConfig:
        enabled_detectors = self.enabled_detector_names
        if not enabled_detectors:
            raise ValueError("At least one analysis detector must be enabled.")
        return AnalyzerConfig(
            history_size=self.history_size,
            enabled_detectors=enabled_detectors,
            enabled_rules=self.enabled_rules,
            thresholds=dict(self.thresholds),
            model_artifact_path=self.model_artifact_path,
            adaptive_correlation_profile_path=self.adaptive_correlation_profile_path,
            isolation_forest_artifact_path=self.isolation_forest_artifact_path,
            model_window_size=self.model_window_size,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_profile": self.model_profile,
            "enabled_models": list(self.enabled_model_names),
            "enabled_detectors": list(self.enabled_detector_names),
            "enabled_rules": (
                None
                if self.enabled_rules is None
                else list(self.enabled_rules)
            ),
            "thresholds": dict(self.thresholds),
            "history_size": self.history_size,
            "model_window_size": self.model_window_size,
            "model_artifact_path": _path_to_str(self.model_artifact_path),
            "adaptive_correlation_profile_path": _path_to_str(
                self.adaptive_correlation_profile_path
            ),
            "isolation_forest_artifact_path": _path_to_str(
                self.isolation_forest_artifact_path
            ),
        }


def _path_to_str(value: str | Path | None) -> str | None:
    if value is None:
        return None
    return str(value)
