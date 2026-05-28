"""GPS spoofing anomaly injector."""

from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class GpsSpoofingInjector:
    """Offsets reported coordinates according to anomaly intensity."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.GPS_SPOOFING

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        offset = 0.001 * intensity
        return replace(
            sample,
            latitude_deg=sample.latitude_deg + offset,
            longitude_deg=sample.longitude_deg + offset,
            gps_eph=500.0,
            gps_epv=500.0,
        )
