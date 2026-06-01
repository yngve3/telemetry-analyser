"""Model-based anomaly detection interfaces."""

from analysis_module.detectors.model_based.adaptive_correlation_based import (
    AdaptiveCorrelationBasedDetector,
    AdaptiveCorrelationProfile,
)
from analysis_module.detectors.model_based.autoencoder import AutoencoderDetector
from analysis_module.detectors.model_based.correlation_based import (
    CorrelationBasedDetector,
)
from analysis_module.detectors.model_based.interfaces import (
    ModelScore,
    NoOpTelemetryScoringModel,
    TelemetryScoringModel,
)
from analysis_module.detectors.model_based.isolation_forest import (
    IsolationForestArtifactModel,
    IsolationForestArtifactScore,
    IsolationForestDetector,
)
from analysis_module.detectors.model_based.model_artifact import (
    ModelArtifact,
    ModelArtifactError,
    ModelArtifactMetadata,
)
from analysis_module.detectors.model_based.model_repository import (
    ModelArtifactRepository,
)
from analysis_module.detectors.model_based.neural_models import (
    AutoencoderArtifactScoringModel,
)
from analysis_module.detectors.model_based.scoring_detector import ScoringDetector

__all__ = [
    "AdaptiveCorrelationBasedDetector",
    "AdaptiveCorrelationProfile",
    "AutoencoderDetector",
    "AutoencoderArtifactScoringModel",
    "CorrelationBasedDetector",
    "IsolationForestArtifactModel",
    "IsolationForestArtifactScore",
    "IsolationForestDetector",
    "ModelArtifact",
    "ModelArtifactError",
    "ModelArtifactMetadata",
    "ModelArtifactRepository",
    "ModelScore",
    "NoOpTelemetryScoringModel",
    "ScoringDetector",
    "TelemetryScoringModel",
]
