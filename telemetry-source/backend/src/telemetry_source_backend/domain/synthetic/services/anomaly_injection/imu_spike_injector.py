"""IMU spike anomaly injector."""

from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class ImuSpikeInjector:
    """Injects abrupt attitude and angular-rate spikes."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.IMU_SPIKE

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        return replace(
            sample,
            roll_rad=(sample.roll_rad or 0.0) + 1.2 * intensity,
            pitch_rad=(sample.pitch_rad or 0.0) - 0.9 * intensity,
            yaw_rad=(sample.yaw_rad or 0.0) + 1.6 * intensity,
            roll_rate_rad_s=(sample.roll_rate_rad_s or 0.0) + 8.0 * intensity,
            pitch_rate_rad_s=(sample.pitch_rate_rad_s or 0.0) - 6.0 * intensity,
            yaw_rate_rad_s=(sample.yaw_rate_rad_s or 0.0) + 5.0 * intensity,
        )
