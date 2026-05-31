"""Service-level registry for analysis models and model profiles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AnalysisModelStatus(StrEnum):
    """Readiness of a service-facing analysis model."""

    AVAILABLE = "available"
    PLANNED = "planned"


class AnalysisModelProfileStatus(StrEnum):
    """Readiness of a model profile."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class AnalysisModelInfo:
    """Description of one model known by analysis-service."""

    name: str
    implementation: str
    status: AnalysisModelStatus
    detector_name: str | None
    description: str
    aliases: tuple[str, ...] = ()

    @property
    def connected(self) -> bool:
        return (
            self.status is AnalysisModelStatus.AVAILABLE
            and self.detector_name is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "implementation": self.implementation,
            "status": self.status.value,
            "detector_name": self.detector_name,
            "connected": self.connected,
            "description": self.description,
            "aliases": list(self.aliases),
        }


@dataclass(frozen=True, slots=True)
class AnalysisModelProfileInfo:
    """Named model composition exposed by analysis-service."""

    name: str
    models: tuple[str, ...]
    description: str

    @property
    def unavailable_models(self) -> tuple[str, ...]:
        return unavailable_model_names(self.models)

    @property
    def status(self) -> AnalysisModelProfileStatus:
        if self.unavailable_models:
            return AnalysisModelProfileStatus.UNAVAILABLE
        return AnalysisModelProfileStatus.AVAILABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "models": list(self.models),
            "enabled_detectors": list(
                detector_names_for_models(self.models, require_available=False)
            ),
            "status": self.status.value,
            "unavailable_models": list(self.unavailable_models),
            "description": self.description,
        }


_MODELS: tuple[AnalysisModelInfo, ...] = (
    AnalysisModelInfo(
        name="rule_based",
        implementation="RuleBasedDetector",
        status=AnalysisModelStatus.AVAILABLE,
        detector_name="rule_based",
        description="Engineering baseline based on explicit telemetry rules.",
    ),
    AnalysisModelInfo(
        name="correlation_based",
        implementation="CorrelationBasedDetector",
        status=AnalysisModelStatus.AVAILABLE,
        detector_name="correlation_based",
        description="Cross-channel and temporal correlation model.",
        aliases=("correlation",),
    ),
    AnalysisModelInfo(
        name="isolation_forest",
        implementation="IsolationForestDetector",
        status=AnalysisModelStatus.AVAILABLE,
        detector_name="isolation_forest",
        description="Trainable baseline for normal-behavior anomaly detection.",
        aliases=("isolationforest",),
    ),
    AnalysisModelInfo(
        name="autoencoder",
        implementation="AutoencoderDetector",
        status=AnalysisModelStatus.AVAILABLE,
        detector_name="autoencoder",
        description="Pluggable reconstruction-error model.",
    ),
    AnalysisModelInfo(
        name="graph_based",
        implementation="GraphBasedDetector",
        status=AnalysisModelStatus.PLANNED,
        detector_name=None,
        description="Future graph-based model for parameter relationship analysis.",
    ),
)

_MODEL_PROFILES: tuple[AnalysisModelProfileInfo, ...] = (
    AnalysisModelProfileInfo(
        name="rules_only",
        models=("rule_based",),
        description="Run only the engineering rule-based baseline.",
    ),
    AnalysisModelProfileInfo(
        name="rules_with_correlation",
        models=("rule_based", "correlation_based"),
        description="Combine rules with cross-parameter correlation analysis.",
    ),
    AnalysisModelProfileInfo(
        name="rules_with_isolation_forest",
        models=("rule_based", "isolation_forest"),
        description="Combine rules with an Isolation Forest baseline.",
    ),
    AnalysisModelProfileInfo(
        name="full_hybrid",
        models=(
            "rule_based",
            "correlation_based",
            "isolation_forest",
            "autoencoder",
        ),
        description=(
            "Run all connected rule, correlation, trainable baseline, "
            "and reconstruction models."
        ),
    ),
)

_MODEL_BY_NAME = {model.name: model for model in _MODELS}
_MODEL_ALIAS_BY_NAME = {
    alias: model.name
    for model in _MODELS
    for alias in (model.name, *model.aliases)
}
_PROFILE_BY_NAME = {profile.name: profile for profile in _MODEL_PROFILES}


def list_analysis_models() -> tuple[AnalysisModelInfo, ...]:
    return _MODELS


def list_model_profiles() -> tuple[AnalysisModelProfileInfo, ...]:
    return _MODEL_PROFILES


def model_names_for_profile(profile_name: str) -> tuple[str, ...]:
    profile = _PROFILE_BY_NAME.get(_normalize_name(profile_name))
    if profile is None:
        supported = ", ".join(sorted(_PROFILE_BY_NAME))
        raise ValueError(
            f"Unknown analysis model profile `{profile_name}`. "
            f"Supported profiles: {supported}."
        )
    return profile.models


def resolve_model_names(model_names: tuple[str, ...]) -> tuple[str, ...]:
    if not model_names:
        raise ValueError("At least one analysis model must be enabled.")
    resolved_names: list[str] = []
    for name in model_names:
        resolved_name = _resolve_model_name(name)
        if resolved_name not in resolved_names:
            resolved_names.append(resolved_name)
    return tuple(resolved_names)


def detector_names_for_models(
    model_names: tuple[str, ...],
    *,
    require_available: bool,
) -> tuple[str, ...]:
    resolved_names = resolve_model_names(model_names)
    unavailable = unavailable_model_names(resolved_names)
    if require_available and unavailable:
        raise ValueError(
            "Analysis models are not available for runtime analysis: "
            f"{', '.join(unavailable)}."
        )
    return tuple(
        model.detector_name
        for model in (_MODEL_BY_NAME[name] for name in resolved_names)
        if model.detector_name is not None
    )


def unavailable_model_names(model_names: tuple[str, ...]) -> tuple[str, ...]:
    resolved_names = resolve_model_names(model_names)
    return tuple(
        name
        for name in resolved_names
        if not _MODEL_BY_NAME[name].connected
    )


def _resolve_model_name(value: str) -> str:
    normalized = _normalize_name(value)
    resolved = _MODEL_ALIAS_BY_NAME.get(normalized)
    if resolved is None:
        supported = ", ".join(sorted(_MODEL_BY_NAME))
        raise ValueError(
            f"Unknown analysis model `{value}`. Supported models: {supported}."
        )
    return resolved


def _normalize_name(value: str) -> str:
    return value.strip().replace("-", "_").lower()
