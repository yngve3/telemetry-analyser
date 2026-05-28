"""Generic anomalous behavior injector."""

from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class AnomalousBehaviorInjector:
    """Applies a mixed anomaly for model-only unexplained behavior."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.ANOMALOUS_BEHAVIOR

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        return replace(
            sample,
            latitude_deg=sample.latitude_deg + 0.0004 * intensity,
            longitude_deg=sample.longitude_deg - 0.0003 * intensity,
            altitude_m=sample.altitude_m + 300.0 * intensity,
            battery_percent=max(0.0, sample.battery_percent - 20.0 * intensity),
            roll_rate_rad_s=(sample.roll_rate_rad_s or 0.0) + 3.0 * intensity,
            yaw_rate_rad_s=(sample.yaw_rate_rad_s or 0.0) - 3.0 * intensity,
            system_status="critical" if intensity >= 0.7 else sample.system_status,
        )
