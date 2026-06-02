"""In-memory analysis session management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from analysis_module import (
    AnomalyResult,
    DetectorPipelineAnalyzer,
    UnifiedTelemetry,
    create_analyzer,
)

from analysis_service.application.profiles import AnalysisProfile
from analysis_service.validation import UnifiedTelemetryValidator


class SessionNotFoundError(KeyError):
    """Raised when an analysis session does not exist."""


@dataclass(slots=True)
class AnalysisSession:
    """Stateful analysis session with an analyzer-owned telemetry history."""

    session_id: str
    profile: AnalysisProfile
    analyzer: DetectorPipelineAnalyzer
    drone_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    last_analyzed_at: datetime | None = None
    samples_analyzed: int = 0
    last_telemetry: UnifiedTelemetry | None = None
    last_result: AnomalyResult | None = None
    telemetry_validator: UnifiedTelemetryValidator = field(
        default_factory=UnifiedTelemetryValidator,
        repr=False,
    )

    def analyze(self, telemetry: UnifiedTelemetry) -> AnomalyResult:
        self.telemetry_validator.validate(telemetry)
        result = self.analyzer.analyze_next(telemetry)
        self.drone_id = telemetry.drone_id
        self.samples_analyzed += 1
        self.last_analyzed_at = datetime.now(tz=UTC)
        self.last_telemetry = telemetry
        self.last_result = result
        return result

    def update_profile(self, profile: AnalysisProfile) -> None:
        self.profile = profile
        self.analyzer = create_analyzer(profile.to_analyzer_config())
        self.last_analyzed_at = None
        self.samples_analyzed = 0
        self.last_telemetry = None
        self.last_result = None

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "drone_id": self.drone_id,
            "created_at": self.created_at.isoformat(),
            "last_analyzed_at": (
                None
                if self.last_analyzed_at is None
                else self.last_analyzed_at.isoformat()
            ),
            "samples_analyzed": self.samples_analyzed,
            "profile": self.profile.to_dict(),
        }


class SessionManager:
    """Coordinates profiles and stateful analyzer sessions."""

    def __init__(self, default_profile: AnalysisProfile | None = None) -> None:
        self._profile = default_profile or AnalysisProfile()
        self._sessions: dict[str, AnalysisSession] = {}
        self._validate_profile(self._profile)

    def get_profile(self) -> AnalysisProfile:
        return self._profile

    def update_profile(self, profile: AnalysisProfile) -> AnalysisProfile:
        self._validate_profile(profile)
        self._profile = profile
        return self._profile

    def create_session(
        self,
        session_id: str | None = None,
        drone_id: str | None = None,
        profile: AnalysisProfile | None = None,
    ) -> AnalysisSession:
        target_profile = profile or self._profile
        analyzer = create_analyzer(target_profile.to_analyzer_config())
        resolved_session_id = session_id or drone_id or str(uuid4())
        if resolved_session_id in self._sessions:
            raise ValueError(f"Analysis session `{resolved_session_id}` already exists.")

        session = AnalysisSession(
            session_id=resolved_session_id,
            profile=target_profile,
            analyzer=analyzer,
            drone_id=drone_id,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> AnalysisSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def update_session_profile(
        self,
        session_id: str,
        profile: AnalysisProfile,
    ) -> AnalysisSession:
        self._validate_profile(profile)
        session = self.get_session(session_id)
        session.update_profile(profile)
        return session

    def delete_session(self, session_id: str) -> AnalysisSession:
        session = self._sessions.pop(session_id, None)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def analyze(self, session_id: str, telemetry: UnifiedTelemetry) -> AnomalyResult:
        return self.get_session(session_id).analyze(telemetry)

    def get_last_result(self, session_id: str) -> AnomalyResult | None:
        return self.get_session(session_id).last_result

    def get_last_telemetry(self, session_id: str) -> UnifiedTelemetry | None:
        return self.get_session(session_id).last_telemetry

    def _validate_profile(self, profile: AnalysisProfile) -> None:
        create_analyzer(profile.to_analyzer_config())
