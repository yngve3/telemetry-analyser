"""Synthetic anomaly injector contract."""

from typing import Protocol

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class AnomalyInjector(Protocol):
    """Strategy that applies one synthetic anomaly type to a telemetry sample."""

    @property
    def anomaly_type(self) -> AnomalyType:
        ...

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        ...

