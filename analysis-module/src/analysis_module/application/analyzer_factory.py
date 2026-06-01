"""Factories for telemetry analyzers."""

from __future__ import annotations

from pathlib import Path

from analysis_module.application.config import AnalyzerConfig
from analysis_module.application.detector import TelemetryDetector
from analysis_module.application.pipeline_analyzer import DetectorPipelineAnalyzer
from analysis_module.detectors.model_based import (
    AdaptiveCorrelationBasedDetector,
    AdaptiveCorrelationProfile,
    AutoencoderDetector,
    CorrelationBasedDetector,
    IsolationForestDetector,
    ModelArtifactError,
    TelemetryScoringModel,
)
from analysis_module.detectors.rule_based.analyzer import RuleBasedTelemetryAnalyzer
from analysis_module.detectors.rule_based.default_rules import create_default_rules
from analysis_module.detectors.rule_based.detector import RuleBasedDetector
from analysis_module.infrastructure.artifacts import FilesystemModelArtifactRepository
from analysis_module.features.telemetry_history import TelemetryHistory


_DETECTOR_NAME_ALIASES = {
    "rule_based": "rule_based",
    "correlation": "correlation_based",
    "correlation_based": "correlation_based",
    "adaptive_correlation": "adaptive_correlation_based",
    "adaptive_correlation_based": "adaptive_correlation_based",
    "isolation_forest": "isolation_forest",
    "isolationforest": "isolation_forest",
    "autoencoder": "autoencoder",
}


class DetectorConfigurationError(ValueError):
    """Raised when requested detectors cannot be created from configuration."""


def create_rule_based_analyzer(
    config: AnalyzerConfig | None = None,
) -> RuleBasedTelemetryAnalyzer:
    """Create a rule-only analyzer with default rule registration."""

    analyzer_config = config or AnalyzerConfig()
    return RuleBasedTelemetryAnalyzer(
        rules=create_default_rules(
            enabled_rules=analyzer_config.enabled_rules,
            thresholds=analyzer_config.thresholds,
        ),
        history=TelemetryHistory(max_size=analyzer_config.history_size),
    )


def create_rule_based_detector(
    config: AnalyzerConfig | None = None,
) -> RuleBasedDetector:
    """Create the rule-based detector used by services and analyzer pipelines."""

    analyzer_config = config or AnalyzerConfig()
    return RuleBasedDetector(
        rules=create_default_rules(
            enabled_rules=analyzer_config.enabled_rules,
            thresholds=analyzer_config.thresholds,
        )
    )


def create_correlation_based_detector(
    config: AnalyzerConfig | None = None,
) -> CorrelationBasedDetector:
    """Create the correlation-based detector."""

    analyzer_config = config or AnalyzerConfig()
    return CorrelationBasedDetector(
        max_ground_speed_delta_m_s=_threshold(
            analyzer_config,
            "correlation_based.max_ground_speed_delta_m_s",
            8.0,
        ),
        max_vertical_speed_delta_m_s=_threshold(
            analyzer_config,
            "correlation_based.max_vertical_speed_delta_m_s",
            3.0,
        ),
        min_position_delta_m=_threshold(
            analyzer_config,
            "correlation_based.min_position_delta_m",
            20.0,
        ),
        min_battery_drop_percent=_threshold(
            analyzer_config,
            "correlation_based.min_battery_drop_percent",
            5.0,
        ),
        min_voltage_drop_v=_threshold(
            analyzer_config,
            "correlation_based.min_voltage_drop_v",
            0.2,
        ),
    )


def create_adaptive_correlation_based_detector(
    config: AnalyzerConfig | None = None,
) -> AdaptiveCorrelationBasedDetector:
    """Create the adaptive correlation-based detector."""

    analyzer_config = config or AnalyzerConfig()
    return AdaptiveCorrelationBasedDetector(
        max_ground_speed_delta_m_s=_threshold(
            analyzer_config,
            "adaptive_correlation_based.max_ground_speed_delta_m_s",
            _threshold(
                analyzer_config,
                "correlation_based.max_ground_speed_delta_m_s",
                8.0,
            ),
        ),
        max_vertical_speed_delta_m_s=_threshold(
            analyzer_config,
            "adaptive_correlation_based.max_vertical_speed_delta_m_s",
            _threshold(
                analyzer_config,
                "correlation_based.max_vertical_speed_delta_m_s",
                3.0,
            ),
        ),
        max_heading_yaw_delta_deg=_threshold(
            analyzer_config,
            "adaptive_correlation_based.max_heading_yaw_delta_deg",
            45.0,
        ),
        min_heading_distance_m=_threshold(
            analyzer_config,
            "adaptive_correlation_based.min_heading_distance_m",
            0.5,
        ),
        min_message_quality=_threshold(
            analyzer_config,
            "adaptive_correlation_based.min_message_quality",
            0.7,
        ),
        profile=AdaptiveCorrelationProfile(
            max_size=_int_threshold(
                analyzer_config,
                "adaptive_correlation_based.profile_size",
                1_000,
            ),
            min_samples=_int_threshold(
                analyzer_config,
                "adaptive_correlation_based.min_profile_samples",
                100,
            ),
            percentile=_threshold(
                analyzer_config,
                "adaptive_correlation_based.percentile",
                0.99,
            ),
            threshold_multiplier=_threshold(
                analyzer_config,
                "adaptive_correlation_based.threshold_multiplier",
                1.2,
            ),
        ),
    )


def create_isolation_forest_detector(
    config: AnalyzerConfig | None = None,
) -> IsolationForestDetector:
    """Create the Isolation Forest detector."""

    analyzer_config = config or AnalyzerConfig()
    return IsolationForestDetector(
        window_size=analyzer_config.model_window_size,
        min_window_size=_int_threshold(
            analyzer_config,
            "isolation_forest.min_window_size",
            8,
        ),
        n_trees=_int_threshold(
            analyzer_config,
            "isolation_forest.n_trees",
            64,
        ),
        subsample_size=_int_threshold(
            analyzer_config,
            "isolation_forest.subsample_size",
            32,
        ),
        score_threshold=_threshold(
            analyzer_config,
            "isolation_forest.score_threshold",
            0.65,
        ),
    )


def create_autoencoder_detector(
    config: AnalyzerConfig | None = None,
) -> AutoencoderDetector:
    """Create the autoencoder-style reconstruction detector."""

    analyzer_config = config or AnalyzerConfig()
    scoring_model = _load_autoencoder_artifact(analyzer_config)
    return AutoencoderDetector(
        window_size=analyzer_config.model_window_size,
        min_window_size=_int_threshold(
            analyzer_config,
            "autoencoder.min_window_size",
            5,
        ),
        reconstruction_error_threshold=_threshold(
            analyzer_config,
            "autoencoder.reconstruction_error_threshold",
            3.0,
        ),
        scoring_model=scoring_model,
    )


def create_detectors(
    config: AnalyzerConfig | None = None,
) -> tuple[TelemetryDetector, ...]:
    """Create detector instances requested by the analyzer configuration."""

    analyzer_config = config or AnalyzerConfig()
    detector_names = []
    for name in analyzer_config.enabled_detectors:
        resolved_name = _resolve_detector_name(name)
        if resolved_name not in detector_names:
            detector_names.append(resolved_name)

    detectors: list[TelemetryDetector] = []
    if "rule_based" in detector_names:
        detectors.append(create_rule_based_detector(analyzer_config))
    if "correlation_based" in detector_names:
        detectors.append(create_correlation_based_detector(analyzer_config))
    if "adaptive_correlation_based" in detector_names:
        detectors.append(create_adaptive_correlation_based_detector(analyzer_config))
    if "isolation_forest" in detector_names:
        detectors.append(create_isolation_forest_detector(analyzer_config))
    if "autoencoder" in detector_names:
        detectors.append(create_autoencoder_detector(analyzer_config))
    return tuple(detectors)


def create_analyzer(config: AnalyzerConfig | None = None) -> DetectorPipelineAnalyzer:
    """Create an analyzer according to the supplied configuration."""

    analyzer_config = config or AnalyzerConfig()
    return DetectorPipelineAnalyzer(
        detectors=create_detectors(analyzer_config),
        history=TelemetryHistory(max_size=analyzer_config.history_size),
        feature_window_size=analyzer_config.model_window_size,
    )


def create_default_analyzer() -> DetectorPipelineAnalyzer:
    """Create the default rule-based telemetry analyzer."""

    return create_analyzer(AnalyzerConfig())


def _normalize_detector_name(value: str) -> str:
    return value.strip().replace("-", "_").lower()


def _resolve_detector_name(value: str) -> str:
    normalized = _normalize_detector_name(value)
    resolved = _DETECTOR_NAME_ALIASES.get(normalized)
    if resolved is None:
        supported = ", ".join(sorted(_DETECTOR_NAME_ALIASES))
        raise DetectorConfigurationError(
            f"Unknown detector `{value}`. Supported detectors: {supported}."
        )
    return resolved


def _threshold(config: AnalyzerConfig, key: str, default: float) -> float:
    return float(config.thresholds.get(key, default))


def _int_threshold(config: AnalyzerConfig, key: str, default: int) -> int:
    return int(_threshold(config, key, float(default)))


def _load_autoencoder_artifact(
    config: AnalyzerConfig,
) -> TelemetryScoringModel | None:
    artifact_path = _resolve_autoencoder_artifact_path(config)
    if artifact_path is None:
        return None

    try:
        return FilesystemModelArtifactRepository().load(artifact_path)
    except ModelArtifactError as exc:
        raise DetectorConfigurationError(str(exc)) from exc


def _resolve_autoencoder_artifact_path(config: AnalyzerConfig) -> Path | None:
    if config.model_artifact_path is not None:
        return Path(config.model_artifact_path)

    module_root = Path(__file__).resolve().parents[3]
    candidates = (
        module_root / "models" / "autoencoder",
        module_root / "models" / "autoencoder.zip",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
