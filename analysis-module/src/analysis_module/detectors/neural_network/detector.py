"""Neural-network detector adapter placeholder."""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis_module.detectors.model_based.interfaces import (
    NoOpTelemetryScoringModel,
    TelemetryScoringModel,
)
from analysis_module.detectors.model_based.scoring_detector import ScoringDetector
from analysis_module.domain import AnomalyType, DetectorKind
from analysis_module.features.feature_extractor import TelemetryFeatureExtractor


@dataclass(frozen=True, slots=True)
class NeuralNetworkTelemetryDetector(ScoringDetector):
    """Scoring detector reserved for neural-network artifacts."""

    model: TelemetryScoringModel = field(default_factory=NoOpTelemetryScoringModel)
    window_size: int = 50
    name: str = "nn_autoencoder"
    kind: DetectorKind = DetectorKind.NN
    anomaly_type: AnomalyType = AnomalyType.ANOMALOUS_BEHAVIOR
    feature_extractor: TelemetryFeatureExtractor = field(
        default_factory=TelemetryFeatureExtractor
    )
