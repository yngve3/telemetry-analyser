"""Shared helpers for lightweight model-based detectors."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt

from analysis_module.application.context import AnalysisContext
from analysis_module.domain import UnifiedTelemetry
from analysis_module.features.feature_extractor import TelemetryFeatureExtractor
from analysis_module.features.feature_window import FeatureWindow


@dataclass(frozen=True, slots=True)
class ResolvedFeatureWindow:
    """Feature window paired with the telemetry samples used to build it."""

    feature_window: FeatureWindow
    samples: tuple[UnifiedTelemetry, ...]


def resolve_feature_window(
    context: AnalysisContext,
    window_size: int,
    feature_extractor: TelemetryFeatureExtractor,
) -> ResolvedFeatureWindow | None:
    samples = (*context.history.samples(), context.current)
    if len(samples) < 2:
        return None

    window_samples = samples[-window_size:]
    return ResolvedFeatureWindow(
        feature_window=feature_extractor.extract_window(window_samples),
        samples=window_samples,
    )


def top_feature_deviations(
    feature_names: Sequence[str],
    reference_rows: Sequence[Sequence[float]],
    current_row: Sequence[float],
    limit: int = 3,
) -> tuple[tuple[str, ...], dict[str, float]]:
    deviations = []
    for index, name in enumerate(feature_names):
        values = [row[index] for row in reference_rows]
        mean = _mean(values)
        scale = _stddev(values)
        if scale <= 1e-9:
            scale = max(abs(mean) * 0.05, 1.0)
        deviations.append((name, abs(current_row[index] - mean) / scale))

    deviations.sort(key=lambda item: item[1], reverse=True)
    top = deviations[:limit]
    return (
        tuple(name for name, _ in top),
        {name: score for name, score in top},
    )


def normalized_rmse(
    reference_rows: Sequence[Sequence[float]],
    current_row: Sequence[float],
) -> float:
    if not reference_rows:
        return 0.0

    errors: list[float] = []
    for index, current_value in enumerate(current_row):
        values = [row[index] for row in reference_rows]
        mean = _mean(values)
        scale = _stddev(values)
        if scale <= 1e-9:
            scale = max(abs(mean) * 0.05, 1.0)
        normalized_error = (current_value - mean) / scale
        errors.append(normalized_error * normalized_error)
    return sqrt(sum(errors) / len(errors))


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return sqrt(variance)
