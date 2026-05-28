"""Analysis profile models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analysis_module import AnalyzerConfig


@dataclass(frozen=True, slots=True)
class AnalysisProfile:
    """Runtime profile used to create analysis-module analyzers."""

    enabled_detectors: tuple[str, ...] = ("rule_based",)
    enabled_rules: tuple[str, ...] | None = None
    thresholds: Mapping[str, float] = field(default_factory=dict)
    history_size: int = 1_000
    model_window_size: int = 50
    model_artifact_path: str | Path | None = None
    ml_model_artifact_path: str | Path | None = None
    nn_model_artifact_path: str | Path | None = None

    def to_analyzer_config(self) -> AnalyzerConfig:
        if not self.enabled_detectors:
            raise ValueError("At least one detector must be enabled.")
        return AnalyzerConfig(
            history_size=self.history_size,
            enabled_detectors=self.enabled_detectors,
            enabled_rules=self.enabled_rules,
            thresholds=dict(self.thresholds),
            model_artifact_path=self.model_artifact_path,
            ml_model_artifact_path=self.ml_model_artifact_path,
            nn_model_artifact_path=self.nn_model_artifact_path,
            model_window_size=self.model_window_size,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled_detectors": list(self.enabled_detectors),
            "enabled_rules": (
                None
                if self.enabled_rules is None
                else list(self.enabled_rules)
            ),
            "thresholds": dict(self.thresholds),
            "history_size": self.history_size,
            "model_window_size": self.model_window_size,
            "model_artifact_path": _path_to_str(self.model_artifact_path),
            "ml_model_artifact_path": _path_to_str(self.ml_model_artifact_path),
            "nn_model_artifact_path": _path_to_str(self.nn_model_artifact_path),
        }


def _path_to_str(value: str | Path | None) -> str | None:
    if value is None:
        return None
    return str(value)
