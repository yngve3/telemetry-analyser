"""Isolation Forest detector implemented with the Python standard library."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from math import ceil, log2
from random import Random

from analysis_module.application.context import AnalysisContext
from analysis_module.detectors.model_based._windowing import (
    resolve_feature_window,
    top_feature_deviations,
)
from analysis_module.domain import (
    AnomalyType,
    DetectedAnomaly,
    DetectorKind,
    DetectorOutput,
    Severity,
)
from analysis_module.features.feature_extractor import TelemetryFeatureExtractor


@dataclass(frozen=True, slots=True)
class IsolationForestDetector:
    """Fits an Isolation Forest baseline on recent telemetry features."""

    name: str = "isolation_forest"
    kind: DetectorKind = DetectorKind.MODEL_BASED
    model_name: str = "isolation_forest_baseline_v1"
    window_size: int = 50
    min_window_size: int = 8
    n_trees: int = 64
    subsample_size: int = 32
    score_threshold: float = 0.65
    random_seed: int = 17
    feature_extractor: TelemetryFeatureExtractor = field(
        default_factory=TelemetryFeatureExtractor
    )

    def analyze(self, context: AnalysisContext) -> DetectorOutput:
        resolved = resolve_feature_window(
            context,
            window_size=self.window_size,
            feature_extractor=self.feature_extractor,
        )
        if resolved is None or len(resolved.feature_window) < self.min_window_size:
            return self._empty_output()

        matrix = resolved.feature_window.values_matrix()
        reference_rows = matrix[:-1]
        current_row = matrix[-1]
        if len(reference_rows) < self.min_window_size - 1:
            return self._empty_output()

        isolation_score = _isolation_score(
            reference_rows=reference_rows,
            current_row=current_row,
            n_trees=self.n_trees,
            subsample_size=self.subsample_size,
            random_seed=self.random_seed,
        )
        affected_parameters, top_scores = top_feature_deviations(
            resolved.feature_window.feature_names,
            reference_rows,
            current_row,
        )
        deviation_score = _deviation_score(top_scores)
        score = max(isolation_score, deviation_score)
        if score <= self.score_threshold:
            return self._empty_output()

        confidence = min(
            1.0,
            0.5 + (score - self.score_threshold) / (1.0 - self.score_threshold),
        )
        anomaly = DetectedAnomaly(
            type=AnomalyType.ANOMALOUS_BEHAVIOR,
            severity=Severity.CRITICAL if score >= 0.85 else Severity.WARNING,
            message="Isolation Forest score exceeded the anomaly threshold.",
            confidence=confidence,
            source=self.kind.value,
            detector_kind=self.kind.value,
            detector_name=self.name,
            model_name=self.model_name,
            score=score,
            affected_parameters=affected_parameters,
            evidence={
                "score": score,
                "isolation_score": isolation_score,
                "deviation_score": deviation_score,
                "threshold": self.score_threshold,
                "window_size": len(resolved.feature_window),
                "reference_size": len(reference_rows),
                "top_feature_scores": top_scores,
            },
            window_start=resolved.samples[0].timestamp,
            window_end=resolved.samples[-1].timestamp,
            probable_cause=(
                "The latest feature vector is isolated from the recent normal "
                "telemetry distribution."
            ),
        )
        return DetectorOutput(
            detector_name=self.name,
            detector_kind=self.kind,
            anomalies=(anomaly,),
        )

    def _empty_output(self) -> DetectorOutput:
        return DetectorOutput(detector_name=self.name, detector_kind=self.kind)


@dataclass(frozen=True, slots=True)
class _IsolationNode:
    size: int
    feature_index: int | None = None
    split_value: float | None = None
    left: "_IsolationNode | None" = None
    right: "_IsolationNode | None" = None


def _isolation_score(
    reference_rows: Sequence[Sequence[float]],
    current_row: Sequence[float],
    n_trees: int,
    subsample_size: int,
    random_seed: int,
) -> float:
    sample_size = min(subsample_size, len(reference_rows))
    if sample_size < 2:
        return 0.0

    rng = Random(random_seed)
    max_depth = ceil(log2(sample_size))
    path_lengths: list[float] = []
    rows = [tuple(row) for row in reference_rows]
    current = tuple(current_row)
    for _ in range(n_trees):
        sample = rng.sample(rows, sample_size)
        tree = _build_tree(sample, depth=0, max_depth=max_depth, rng=rng)
        path_lengths.append(_path_length(current, tree, current_depth=0))

    average_path = sum(path_lengths) / len(path_lengths)
    normalizer = _average_path_length(sample_size)
    if normalizer <= 0.0:
        return 0.0
    return 2 ** (-average_path / normalizer)


def _build_tree(
    rows: Sequence[Sequence[float]],
    depth: int,
    max_depth: int,
    rng: Random,
) -> _IsolationNode:
    if depth >= max_depth or len(rows) <= 1:
        return _IsolationNode(size=len(rows))

    variable_features = _variable_features(rows)
    if not variable_features:
        return _IsolationNode(size=len(rows))

    feature_index = rng.choice(variable_features)
    values = [row[feature_index] for row in rows]
    min_value = min(values)
    max_value = max(values)
    split_value = rng.uniform(min_value, max_value)
    left_rows = [row for row in rows if row[feature_index] < split_value]
    right_rows = [row for row in rows if row[feature_index] >= split_value]
    if not left_rows or not right_rows:
        return _IsolationNode(size=len(rows))

    return _IsolationNode(
        size=len(rows),
        feature_index=feature_index,
        split_value=split_value,
        left=_build_tree(left_rows, depth + 1, max_depth, rng),
        right=_build_tree(right_rows, depth + 1, max_depth, rng),
    )


def _path_length(
    row: Sequence[float],
    node: _IsolationNode,
    current_depth: int,
) -> float:
    if node.feature_index is None or node.split_value is None:
        return current_depth + _average_path_length(node.size)

    if row[node.feature_index] < node.split_value:
        if node.left is None:
            return current_depth
        return _path_length(row, node.left, current_depth + 1)

    if node.right is None:
        return current_depth
    return _path_length(row, node.right, current_depth + 1)


def _variable_features(rows: Sequence[Sequence[float]]) -> tuple[int, ...]:
    feature_count = len(rows[0])
    result = []
    for index in range(feature_count):
        values = [row[index] for row in rows]
        if min(values) < max(values):
            result.append(index)
    return tuple(result)


def _average_path_length(size: int) -> float:
    if size <= 1:
        return 0.0
    if size == 2:
        return 1.0
    harmonic = sum(1.0 / value for value in range(1, size))
    return 2.0 * harmonic - (2.0 * (size - 1) / size)


def _deviation_score(top_scores: dict[str, float]) -> float:
    if not top_scores:
        return 0.0
    highest_score = max(top_scores.values())
    return min(0.99, highest_score / (highest_score + 8.0))
