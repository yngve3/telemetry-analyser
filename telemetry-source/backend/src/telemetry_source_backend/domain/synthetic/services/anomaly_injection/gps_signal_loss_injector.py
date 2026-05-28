"""GPS signal loss anomaly injector."""

from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class GpsSignalLossInjector:
    """Degrades GPS fix quality and satellite visibility."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.GPS_SIGNAL_LOSS

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        satellites = max(0, round(sample.satellites * (1.0 - intensity)))
        fix_type = 1 if satellites < 4 else sample.gps_fix_type or 3
        return replace(
            sample,
            satellites=satellites,
            satellites_visible=satellites,
            gps_fix_type=fix_type,
            gps_eph=100.0 + 9_000.0 * intensity,
            gps_epv=150.0 + 9_000.0 * intensity,
        )
