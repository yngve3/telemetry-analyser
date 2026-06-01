"""Detector contracts used by services and analyzer factories."""

from typing import Protocol, runtime_checkable

from analysis_module.application.context import AnalysisContext
from analysis_module.domain import DetectorKind, DetectorOutput


class TelemetryDetector(Protocol):
    """Detector contract for analysis-service orchestration."""

    @property
    def name(self) -> str:
        """Detector public name."""
        ...

    @property
    def kind(self) -> DetectorKind:
        """Detector family."""
        ...

    def analyze(self, context: AnalysisContext) -> DetectorOutput:
        """Analyze one telemetry sample using a read-only context."""
        ...


@runtime_checkable
class ProfileFeedbackDetector(Protocol):
    """Detector that updates an internal profile after final aggregation."""

    def commit_profile_update(self) -> None:
        """Apply the last pending profile update."""
        ...

    def discard_profile_update(self) -> None:
        """Drop the last pending profile update."""
        ...
