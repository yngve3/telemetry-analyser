"""Analysis profile API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from analysis_service.application import AnalysisProfile


class AnalysisProfileRequest(BaseModel):
    enabled_detectors: list[str] = Field(default_factory=lambda: ["rule_based"])
    enabled_rules: list[str] | None = None
    thresholds: dict[str, float] = Field(default_factory=dict)
    history_size: int = Field(default=1_000, gt=0)
    model_window_size: int = Field(default=50, gt=0)
    model_artifact_path: str | None = None
    ml_model_artifact_path: str | None = None
    nn_model_artifact_path: str | None = None

    def to_profile(self) -> AnalysisProfile:
        return AnalysisProfile(
            enabled_detectors=tuple(self.enabled_detectors),
            enabled_rules=(
                None
                if self.enabled_rules is None
                else tuple(self.enabled_rules)
            ),
            thresholds=dict(self.thresholds),
            history_size=self.history_size,
            model_window_size=self.model_window_size,
            model_artifact_path=self.model_artifact_path,
            ml_model_artifact_path=self.ml_model_artifact_path,
            nn_model_artifact_path=self.nn_model_artifact_path,
        )


class AnalysisProfileResponse(AnalysisProfileRequest):
    @classmethod
    def from_profile(cls, profile: AnalysisProfile) -> "AnalysisProfileResponse":
        return cls(**profile.to_dict())
