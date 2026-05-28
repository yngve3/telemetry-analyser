"""Factories for telemetry analyzers."""

from __future__ import annotations

from pathlib import Path

from analysis_module.application.config import AnalyzerConfig
from analysis_module.application.detector import TelemetryDetector
from analysis_module.application.pipeline_analyzer import DetectorPipelineAnalyzer
from analysis_module.detectors.model_based.interfaces import (
    TelemetryScoringModel,
)
from analysis_module.detectors.ml_based import MlTelemetryDetector
from analysis_module.detectors.neural_network import NeuralNetworkTelemetryDetector
from analysis_module.detectors.rule_based.analyzer import RuleBasedTelemetryAnalyzer
from analysis_module.detectors.rule_based.default_rules import create_default_rules
from analysis_module.detectors.rule_based.detector import RuleBasedDetector
from analysis_module.features.telemetry_history import TelemetryHistory
from analysis_module.infrastructure.artifacts.filesystem_model_repository import (
    FilesystemModelArtifactRepository,
)


_DETECTOR_NAME_ALIASES = {
    "rule_based": "rule_based",
    "ml": "ml",
    "nn": "nn",
    "neural_network": "nn",
    "nn_autoencoder": "nn",
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


def create_ml_detector(config: AnalyzerConfig | None = None) -> MlTelemetryDetector:
    """Create an artifact-backed ML scoring detector."""

    analyzer_config = config or AnalyzerConfig()
    artifact_path = analyzer_config.ml_model_artifact_path
    if artifact_path is None:
        artifact_path = analyzer_config.model_artifact_path
    model = _load_required_model(artifact_path, "ml")
    return MlTelemetryDetector(
        model=model,
        window_size=analyzer_config.model_window_size,
    )


def create_neural_network_detector(
    config: AnalyzerConfig | None = None,
) -> NeuralNetworkTelemetryDetector:
    """Create an artifact-backed neural-network detector."""

    analyzer_config = config or AnalyzerConfig()
    model = _load_required_model(analyzer_config.nn_model_artifact_path, "nn")
    return NeuralNetworkTelemetryDetector(
        model=model,
        window_size=analyzer_config.model_window_size,
    )


def create_detectors(
    config: AnalyzerConfig | None = None,
) -> tuple[TelemetryDetector, ...]:
    """Create detector instances requested by the analyzer configuration."""

    analyzer_config = config or AnalyzerConfig()
    detector_names = {
        _resolve_detector_name(name)
        for name in analyzer_config.enabled_detectors
    }
    if analyzer_config.enable_model_detector:
        detector_names.add("ml")

    detectors: list[TelemetryDetector] = []
    if "rule_based" in detector_names:
        detectors.append(create_rule_based_detector(analyzer_config))
    if "ml" in detector_names:
        detectors.append(create_ml_detector(analyzer_config))
    if "nn" in detector_names:
        detectors.append(create_neural_network_detector(analyzer_config))
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


def _load_required_model(
    path: str | Path | None,
    detector_name: str,
) -> TelemetryScoringModel:
    if path is None:
        raise DetectorConfigurationError(
            f"Detector `{detector_name}` requires a model artifact path."
        )
    return FilesystemModelArtifactRepository().load(path)


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
