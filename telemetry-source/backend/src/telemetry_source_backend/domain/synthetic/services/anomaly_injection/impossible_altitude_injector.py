"""Impossible altitude anomaly injector."""

from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class ImpossibleAltitudeInjector:
    """Moves altitude outside the expected physical range."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.IMPOSSIBLE_ALTITUDE

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        return replace(sample, altitude_m=30_000.0 + intensity * 10_000.0)

