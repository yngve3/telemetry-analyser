"""Analysis profile API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from analysis_service.application import AnalysisProfile


class AnalysisProfileRequest(BaseModel):
    model_profile: str = "rules_only"
    enabled_models: list[str] | None = None
    enabled_detectors: list[str] | None = None
    enabled_rules: list[str] | None = None
    thresholds: dict[str, float] = Field(default_factory=dict)
    history_size: int = Field(default=1_000, gt=0)
    model_window_size: int = Field(default=50, gt=0)
    model_artifact_path: str | None = None
    adaptive_correlation_profile_path: str | None = None
    isolation_forest_artifact_path: str | None = None

    def to_profile(self) -> AnalysisProfile:
        enabled_models = self.enabled_models
        if enabled_models is None and self.enabled_detectors is not None:
            enabled_models = self.enabled_detectors
        return AnalysisProfile(
            model_profile=self.model_profile,
            enabled_models=(
                None
                if enabled_models is None
                else tuple(enabled_models)
            ),
            enabled_rules=(
                None
                if self.enabled_rules is None
                else tuple(self.enabled_rules)
            ),
            thresholds=dict(self.thresholds),
            history_size=self.history_size,
            model_window_size=self.model_window_size,
            model_artifact_path=self.model_artifact_path,
            adaptive_correlation_profile_path=self.adaptive_correlation_profile_path,
            isolation_forest_artifact_path=self.isolation_forest_artifact_path,
        )


class AnalysisProfileResponse(AnalysisProfileRequest):
    @classmethod
    def from_profile(cls, profile: AnalysisProfile) -> "AnalysisProfileResponse":
        return cls(**profile.to_dict())
