"""Telemetry freeze anomaly injector."""

from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class TelemetryFreezeInjector:
    """Freezes timestamp buckets and movement values."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.TELEMETRY_FREEZE

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        frozen_second = sample.timestamp.second - sample.timestamp.second % 10
        frozen_timestamp = sample.timestamp.replace(
            second=frozen_second,
            microsecond=0,
        )
        return replace(
            sample,
            timestamp=frozen_timestamp,
            ground_speed_m_s=0.0,
            vertical_speed_m_s=0.0,
            velocity_x_m_s=0.0,
            velocity_y_m_s=0.0,
            velocity_z_m_s=0.0,
            roll_rate_rad_s=0.0,
            pitch_rate_rad_s=0.0,
            yaw_rate_rad_s=0.0,
        )
