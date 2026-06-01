"""Feature-group diagnostics for model anomaly explanations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import isfinite, sqrt
from typing import Any

from analysis_module.domain import AnomalyReason


REASON_GROUPS: Mapping[str, tuple[str, ...]] = {
    "GPS": (
        "gps_fix_status",
        "gps_fix_status_mean",
        "satellites_visible",
        "satellites_visible_mean",
        "eph",
        "eph_mean",
        "epv",
        "epv_mean",
        "gps_check_fail_flags",
        "gps_check_fail_flags_max",
        "global_position_invalid",
        "global_position_invalid_max",
    ),
    "Speed and position": (
        "position_speed_error",
        "position_speed_error_mean",
        "position_speed_error_max",
        "ground_speed",
        "ground_speed_mean",
        "ground_speed_std",
        "vx",
        "vy",
        "pos_test_ratio",
        "pos_test_ratio_mean",
        "pos_test_ratio_max",
        "vel_test_ratio",
        "vel_test_ratio_mean",
        "vel_test_ratio_max",
    ),
    "Altitude": (
        "altitude",
        "altitude_delta",
        "altitude_velocity_error",
        "altitude_velocity_error_mean",
        "altitude_velocity_error_max",
        "hgt_test_ratio",
        "hgt_test_ratio_mean",
        "hgt_test_ratio_max",
        "vz",
        "vertical_speed_mean",
        "vertical_speed_std",
    ),
    "Orientation": (
        "roll",
        "roll_mean",
        "roll_std",
        "pitch",
        "pitch_mean",
        "pitch_std",
        "yaw",
        "yaw_mean",
        "yaw_std",
        "yaw_delta",
        "heading_yaw_error",
        "heading_yaw_error_mean",
        "heading_yaw_error_max",
        "attitude_invalid",
        "attitude_invalid_max",
        "angular_velocity_invalid",
        "angular_velocity_invalid_max",
    ),
    "Battery": (
        "battery_voltage",
        "battery_voltage_mean",
        "battery_remaining",
        "battery_remaining_mean",
        "battery_warning",
        "battery_warning_max",
        "fd_battery",
        "fd_battery_max",
    ),
    "Estimator": (
        "mag_test_ratio",
        "mag_test_ratio_mean",
        "mag_test_ratio_max",
        "hdg_test_ratio",
        "hdg_test_ratio_mean",
        "hdg_test_ratio_max",
        "filter_fault_flags",
        "filter_fault_flags_max",
        "innovation_check_flags",
        "innovation_check_flags_max",
    ),
    "Failsafe": (
        "local_position_invalid",
        "local_position_invalid_max",
        "local_velocity_invalid",
        "local_velocity_invalid_max",
        "fd_motor_failure",
        "fd_motor_failure_max",
        "fd_critical_failure",
        "fd_critical_failure_max",
        "fd_roll",
        "fd_roll_max",
        "fd_pitch",
        "fd_pitch_max",
        "fd_alt",
        "fd_alt_max",
        "fd_motor",
        "fd_motor_max",
        "fd_imbalanced_prop",
        "fd_imbalanced_prop_max",
    ),
}


@dataclass(frozen=True, slots=True)
class FeatureStatistics:
    """Normal-behavior statistics for one trained feature."""

    mean: float
    std: float
    minimum: float | None = None
    maximum: float | None = None

    def z_score(self, value: float) -> float:
        if not isfinite(value):
            return 0.0
        scale = self.std
        if scale <= 1e-9:
            scale = max(abs(self.mean) * 0.05, 1.0)
        return abs(value - self.mean) / scale


@dataclass(frozen=True, slots=True)
class ReasonDiagnosticsResult:
    """Ranked feature and group deviations for one anomalous window."""

    reasons: tuple[AnomalyReason, ...]
    feature_scores: Mapping[str, float] = field(default_factory=dict)
    group_scores: Mapping[str, float] = field(default_factory=dict)

    def top_features(self, limit: int = 3) -> tuple[str, ...]:
        ranked = sorted(
            self.feature_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return tuple(name for name, _ in ranked[:limit])

    def top_feature_scores(self, limit: int = 3) -> dict[str, float]:
        ranked = sorted(
            self.feature_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return {name: score for name, score in ranked[:limit]}

    def to_evidence(self) -> dict[str, Any]:
        return {
            "reasons": [reason.to_dict() for reason in self.reasons],
            "feature_deviation_scores": dict(self.feature_scores),
            "reason_group_scores": dict(self.group_scores),
        }


@dataclass(frozen=True, slots=True)
class ReasonDiagnostics:
    """Calculates likely anomaly reasons from trained feature statistics."""

    groups: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: dict(REASON_GROUPS)
    )
    reason_limit: int = 3
    features_per_reason: int = 3

    def diagnose(
        self,
        feature_values: Mapping[str, float],
        statistics: Mapping[str, FeatureStatistics],
    ) -> ReasonDiagnosticsResult:
        feature_scores = _feature_scores(feature_values, statistics)
        group_scores: dict[str, float] = {}
        reasons: list[AnomalyReason] = []

        for group, group_features in self.groups.items():
            group_feature_scores = {
                feature: feature_scores[feature]
                for feature in group_features
                if feature in feature_scores
            }
            if not group_feature_scores:
                continue

            score = max(group_feature_scores.values())
            if score <= 0.0:
                continue

            group_scores[group] = score
            top_features = _top_scores(group_feature_scores, self.features_per_reason)
            reasons.append(
                AnomalyReason(
                    group=group,
                    score=score,
                    confidence=_reason_confidence(score),
                    features=tuple(top_features),
                    feature_scores=top_features,
                    description=(
                        f"{group} features have the largest deviation from "
                        "the trained normal-behavior profile."
                    ),
                )
            )

        reasons.sort(key=lambda reason: reason.score, reverse=True)
        return ReasonDiagnosticsResult(
            reasons=tuple(reasons[: self.reason_limit]),
            feature_scores=feature_scores,
            group_scores=group_scores,
        )


def feature_statistics_from_metadata(
    feature_names: Sequence[str],
    metadata: Mapping[str, Any],
    scaler: Any | None = None,
) -> dict[str, FeatureStatistics]:
    """Build feature statistics from saved metadata and scaler attributes."""

    result = _metadata_feature_statistics(feature_names, metadata)
    scaler_statistics = feature_statistics_from_scaler(feature_names, scaler)
    for name, statistics in scaler_statistics.items():
        result.setdefault(name, statistics)
    return result


def feature_statistics_from_scaler(
    feature_names: Sequence[str],
    scaler: Any | None,
) -> dict[str, FeatureStatistics]:
    if scaler is None:
        return {}

    means = _number_sequence(getattr(scaler, "mean_", None))
    scales = _number_sequence(getattr(scaler, "scale_", None))
    variances = _number_sequence(getattr(scaler, "var_", None))
    if not means:
        return {}

    feature_count = len(feature_names)
    if feature_count == 0:
        return {}

    if len(means) == feature_count:
        return {
            feature_names[index]: FeatureStatistics(
                mean=means[index],
                std=_std_at(index, scales, variances),
            )
            for index in range(feature_count)
        }

    if len(means) % feature_count != 0:
        return {}

    result: dict[str, FeatureStatistics] = {}
    for feature_index, feature_name in enumerate(feature_names):
        indexes = range(feature_index, len(means), feature_count)
        feature_means = [means[index] for index in indexes]
        feature_scales = [
            _std_at(index, scales, variances)
            for index in indexes
        ]
        result[feature_name] = FeatureStatistics(
            mean=sum(feature_means) / len(feature_means),
            std=sum(feature_scales) / len(feature_scales),
        )
    return result


def _metadata_feature_statistics(
    feature_names: Sequence[str],
    metadata: Mapping[str, Any],
) -> dict[str, FeatureStatistics]:
    payload = metadata.get("feature_statistics")
    if not isinstance(payload, Mapping):
        return {}

    result: dict[str, FeatureStatistics] = {}
    for name in feature_names:
        raw_statistics = payload.get(name)
        if not isinstance(raw_statistics, Mapping):
            continue
        mean = _number(raw_statistics.get("mean"))
        std = _number(raw_statistics.get("std"))
        if mean is None or std is None:
            continue
        result[name] = FeatureStatistics(
            mean=mean,
            std=std,
            minimum=_number(raw_statistics.get("min")),
            maximum=_number(raw_statistics.get("max")),
        )
    return result


def _feature_scores(
    feature_values: Mapping[str, float],
    statistics: Mapping[str, FeatureStatistics],
) -> dict[str, float]:
    result: dict[str, float] = {}
    for feature_name, value in feature_values.items():
        feature_statistics = statistics.get(feature_name)
        if feature_statistics is None:
            continue
        result[feature_name] = feature_statistics.z_score(float(value))
    return result


def _top_scores(scores: Mapping[str, float], limit: int) -> dict[str, float]:
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return {name: score for name, score in ranked[:limit]}


def _reason_confidence(score: float) -> float:
    return min(1.0, max(0.0, score / (score + 3.0)))


def _number_sequence(value: Any) -> list[float]:
    if value is None:
        return []
    try:
        return [float(item) for item in value]
    except TypeError:
        return []


def _std_at(index: int, scales: Sequence[float], variances: Sequence[float]) -> float:
    if index < len(scales):
        return max(float(scales[index]), 0.0)
    if index < len(variances):
        return sqrt(max(float(variances[index]), 0.0))
    return 0.0


def _number(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None
