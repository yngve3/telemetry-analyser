"""Isolation Forest detector implemented with the Python standard library."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import ceil, degrees, log2
from random import Random
from typing import Any
from warnings import catch_warnings, simplefilter

from analysis_module.application.context import AnalysisContext
from analysis_module.application.reason_diagnostics import (
    FeatureStatistics,
    ReasonDiagnostics,
    ReasonDiagnosticsResult,
)
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
    UnifiedTelemetry,
)
from analysis_module.features.feature_extractor import TelemetryFeatureExtractor
from analysis_module.features.feature_extractor import distance_meters, elapsed_seconds
from analysis_module.features.model_features import extract_window_feature_values


@dataclass(frozen=True, slots=True)
class IsolationForestArtifactScore:
    """Decision score returned by a trained Isolation Forest artifact."""

    raw_score: float
    anomaly_margin: float
    confidence: float
    feature_values: Mapping[str, float]
    threshold: float
    diagnostics: ReasonDiagnosticsResult | None = None


@dataclass(frozen=True, slots=True)
class IsolationForestArtifactModel:
    """Loaded sklearn Isolation Forest artifact and its feature contract."""

    model: Any
    scaler: Any
    feature_names: tuple[str, ...]
    threshold: float
    window_size: int
    metadata: Mapping[str, Any] = field(default_factory=dict)
    feature_statistics: Mapping[str, FeatureStatistics] = field(default_factory=dict)
    reason_diagnostics: ReasonDiagnostics = field(default_factory=ReasonDiagnostics)

    def score(self, samples: Sequence["UnifiedTelemetry"]) -> IsolationForestArtifactScore:
        feature_values = _extract_artifact_features(samples, self.feature_names)
        row = [[feature_values[name] for name in self.feature_names]]
        with catch_warnings():
            simplefilter("ignore", UserWarning)
            scaled_row = self.scaler.transform(row)
        raw_score = float(self.model.decision_function(scaled_row)[0])
        anomaly_margin = max(0.0, self.threshold - raw_score)
        confidence = 0.0
        if anomaly_margin > 0.0:
            confidence = min(
                1.0,
                0.5 + anomaly_margin / _artifact_score_scale(self.metadata),
            )
        return IsolationForestArtifactScore(
            raw_score=raw_score,
            anomaly_margin=anomaly_margin,
            confidence=confidence,
            feature_values=feature_values,
            threshold=self.threshold,
            diagnostics=(
                self.reason_diagnostics.diagnose(
                    feature_values,
                    self.feature_statistics,
                )
                if self.feature_statistics
                else None
            ),
        )


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
    artifact_model: IsolationForestArtifactModel | None = None
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

        if self.artifact_model is not None:
            return self._analyze_artifact(resolved.samples)

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
        feature_values = {
            name: current_row[index]
            for index, name in enumerate(resolved.feature_window.feature_names)
        }
        diagnostics = ReasonDiagnostics().diagnose(
            feature_values,
            _reference_statistics(
                resolved.feature_window.feature_names,
                reference_rows,
            ),
        )
        if diagnostics.reasons:
            affected_parameters = diagnostics.top_features() or affected_parameters
            top_scores = diagnostics.top_feature_scores() or top_scores
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
            diagnostic_evidence=(
                diagnostics.to_evidence()
                if diagnostics.reasons
                else {}
            ),
            reasons=diagnostics.reasons,
        )
        return DetectorOutput(
            detector_name=self.name,
            detector_kind=self.kind,
            anomalies=(anomaly,),
        )

    def _analyze_artifact(
        self,
        samples: Sequence["UnifiedTelemetry"],
    ) -> DetectorOutput:
        if self.artifact_model is None:
            return self._empty_output()

        artifact_score = self.artifact_model.score(samples)
        if artifact_score.anomaly_margin <= 0.0:
            return self._empty_output()

        diagnostics = artifact_score.diagnostics
        if diagnostics is not None and diagnostics.reasons:
            affected_parameters = diagnostics.top_features()
            top_feature_values = diagnostics.top_feature_scores()
            diagnostic_evidence = diagnostics.to_evidence()
            reasons = diagnostics.reasons
        else:
            affected_parameters, top_feature_values = _top_artifact_features(
                artifact_score.feature_values
            )
            diagnostic_evidence = {}
            reasons = ()
        anomaly = DetectedAnomaly(
            type=AnomalyType.ANOMALOUS_BEHAVIOR,
            severity=(
                Severity.CRITICAL
                if artifact_score.confidence >= 0.85
                else Severity.WARNING
            ),
            message="Trained Isolation Forest artifact marked the telemetry window as anomalous.",
            confidence=artifact_score.confidence,
            source=self.kind.value,
            detector_kind=self.kind.value,
            detector_name=self.name,
            model_name=self.model_name,
            score=artifact_score.anomaly_margin,
            affected_parameters=affected_parameters,
            evidence={
                "raw_decision_score": artifact_score.raw_score,
                "decision_threshold": artifact_score.threshold,
                "anomaly_margin": artifact_score.anomaly_margin,
                "window_size": len(samples),
                "artifact_window_size": self.artifact_model.window_size,
                "artifact_feature_names": self.artifact_model.feature_names,
                "top_feature_values": top_feature_values,
                "artifact_metadata": dict(self.artifact_model.metadata),
            },
            window_start=samples[0].timestamp,
            window_end=samples[-1].timestamp,
            probable_cause=(
                "The trained Isolation Forest model classified the telemetry "
                "window as outside the learned normal distribution."
            ),
            diagnostic_evidence=diagnostic_evidence,
            reasons=reasons,
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


def _extract_artifact_features(
    samples: Sequence["UnifiedTelemetry"],
    feature_names: Sequence[str],
) -> dict[str, float]:
    return extract_window_feature_values(samples, feature_names)


def _reference_statistics(
    feature_names: Sequence[str],
    reference_rows: Sequence[Sequence[float]],
) -> dict[str, FeatureStatistics]:
    result: dict[str, FeatureStatistics] = {}
    for index, name in enumerate(feature_names):
        values = [row[index] for row in reference_rows]
        result[name] = FeatureStatistics(
            mean=_mean(values),
            std=_stddev(values),
            minimum=min(values) if values else None,
            maximum=max(values) if values else None,
        )
    return result


def _consistency_errors(
    samples: Sequence["UnifiedTelemetry"],
) -> dict[str, list[float]]:
    result = {
        "position_speed_error": [],
        "altitude_velocity_error": [],
        "heading_yaw_error": [],
    }
    for previous, current in zip(samples, samples[1:]):
        elapsed_sec = elapsed_seconds(previous, current)
        if elapsed_sec <= 0.02 or elapsed_sec > 2.0:
            continue

        distance_delta_m = distance_meters(previous, current)
        speed = current.ground_speed_m_s
        if speed is not None:
            result["position_speed_error"].append(
                abs(distance_delta_m / elapsed_sec - speed)
            )

        vertical_speed = _vertical_speed(current)
        if vertical_speed is not None:
            altitude_delta_m = current.altitude_m - previous.altitude_m
            result["altitude_velocity_error"].append(
                abs(altitude_delta_m / elapsed_sec - vertical_speed)
            )

        yaw_deg = _yaw_deg(current)
        if yaw_deg is not None and distance_delta_m > 0.5:
            heading_deg = _bearing_degrees(previous, current)
            result["heading_yaw_error"].append(
                abs((heading_deg - yaw_deg + 180.0) % 360.0 - 180.0)
            )
    return result


def _top_artifact_features(
    values: Mapping[str, float],
    limit: int = 3,
) -> tuple[tuple[str, ...], dict[str, float]]:
    ranked = sorted(values.items(), key=lambda item: abs(item[1]), reverse=True)
    top = ranked[:limit]
    return tuple(name for name, _ in top), {name: value for name, value in top}


def _ground_speeds(samples: Sequence["UnifiedTelemetry"]) -> list[float]:
    return [
        value
        for sample in samples
        if (value := sample.ground_speed_m_s) is not None
    ]


def _vertical_speeds(samples: Sequence["UnifiedTelemetry"]) -> list[float]:
    return [
        value
        for sample in samples
        if (value := _vertical_speed(sample)) is not None
    ]


def _vertical_speed(sample: "UnifiedTelemetry") -> float | None:
    if sample.vertical_speed_m_s is not None:
        return sample.vertical_speed_m_s
    return sample.velocity_z_m_s


def _angles_deg(samples: Sequence["UnifiedTelemetry"], field_name: str) -> list[float]:
    result = []
    for sample in samples:
        value = getattr(sample, field_name)
        if value is not None:
            result.append(degrees(value))
    return result


def _yaw_values(samples: Sequence["UnifiedTelemetry"]) -> list[float]:
    result = []
    for sample in samples:
        yaw = _yaw_deg(sample)
        if yaw is not None:
            result.append(yaw)
    return result


def _yaw_deg(sample: "UnifiedTelemetry") -> float | None:
    if sample.yaw_rad is not None:
        return degrees(sample.yaw_rad) % 360.0
    if sample.heading_deg is not None:
        return sample.heading_deg % 360.0
    return None


def _optional_values(
    samples: Sequence["UnifiedTelemetry"],
    field_name: str,
) -> list[float]:
    result = []
    for sample in samples:
        value = getattr(sample, field_name)
        if value is not None:
            result.append(float(value))
    return result


def _satellite_values(samples: Sequence["UnifiedTelemetry"]) -> list[float]:
    result = []
    for sample in samples:
        value = (
            sample.satellites_visible
            if sample.satellites_visible is not None
            else sample.satellites
        )
        result.append(float(value))
    return result


def _angle_delta(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0] + 180.0) % 360.0 - 180.0


def _bearing_degrees(
    previous: "UnifiedTelemetry",
    current: "UnifiedTelemetry",
) -> float:
    from math import atan2, cos, radians, sin

    previous_lat = radians(previous.latitude_deg)
    current_lat = radians(current.latitude_deg)
    delta_lon = radians(current.longitude_deg - previous.longitude_deg)
    y = sin(delta_lon) * cos(current_lat)
    x = (
        cos(previous_lat) * sin(current_lat)
        - sin(previous_lat) * cos(current_lat) * cos(delta_lon)
    )
    return (degrees(atan2(y, x)) + 360.0) % 360.0


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5


def _max(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return max(values)


def _artifact_score_scale(metadata: Mapping[str, Any]) -> float:
    percentiles = metadata.get("score_percentiles", {})
    if isinstance(percentiles, Mapping):
        p01 = percentiles.get("p01")
        p95 = percentiles.get("p95")
        if isinstance(p01, int | float) and isinstance(p95, int | float):
            return max(abs(float(p95) - float(p01)), 1e-9)
    return max(abs(float(metadata.get("threshold", 0.0))), 1e-9)
