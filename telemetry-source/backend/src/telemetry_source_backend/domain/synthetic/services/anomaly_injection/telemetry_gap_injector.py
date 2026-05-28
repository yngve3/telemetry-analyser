"""Telemetry gap anomaly injector."""

from dataclasses import replace
from datetime import timedelta

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class TelemetryGapInjector:
    """Creates an abnormal timestamp jump in generated telemetry."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.TELEMETRY_GAP

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        return replace(
            sample,
            timestamp=sample.timestamp + timedelta(seconds=5.0 + 15.0 * intensity),
        )
