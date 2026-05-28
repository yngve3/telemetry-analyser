"""Analysis context passed to detector implementations."""

from __future__ import annotations

from dataclasses import dataclass

from analysis_module.domain import TelemetryHistoryView, UnifiedTelemetry
from analysis_module.features.feature_window import FeatureWindow


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    """Read-only context for detector execution."""

    current: UnifiedTelemetry
    history: TelemetryHistoryView
    feature_window: FeatureWindow | None = None
