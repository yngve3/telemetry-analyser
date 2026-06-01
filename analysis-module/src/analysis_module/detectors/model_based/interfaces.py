"""Interfaces for future model-based telemetry scoring."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import inf
from typing import Any, Protocol

from analysis_module.domain import AnomalyReason
from analysis_module.features.feature_window import FeatureWindow


@dataclass(frozen=True, slots=True)
class ModelScore:
    """Score returned by a telemetry anomaly scoring model."""

    score: float
    threshold: float
    confidence: float
    metadata: Mapping[str, Any] = field(default_factory=dict)
    feature_scores: Mapping[str, float] = field(default_factory=dict)
    reasons: tuple[AnomalyReason, ...] = ()


class TelemetryScoringModel(Protocol):
    """Contract for model-based telemetry anomaly scoring."""

    def score(self, feature_window: FeatureWindow) -> ModelScore:
        """Score a feature window."""
        ...


@dataclass(frozen=True, slots=True)
class NoOpTelemetryScoringModel:
    """Model stub used until a trained artifact loader is added."""

    threshold: float = inf
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def score(self, feature_window: FeatureWindow) -> ModelScore:
        del feature_window
        return ModelScore(
            score=0.0,
            threshold=self.threshold,
            confidence=0.0,
            metadata=self.metadata,
        )
