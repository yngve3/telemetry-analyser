"""Motion inconsistency anomaly injector."""

from dataclasses import replace
from math import cos, radians, sin

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class MotionInconsistencyInjector:
    """Makes scalar speed and velocity vector contradict each other."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.MOTION_INCONSISTENCY

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        heading_rad = radians(sample.heading_deg or 0.0)
        reported_speed = (sample.ground_speed_m_s or 0.0) + 20.0 * intensity
        vector_speed = reported_speed + 15.0 * intensity
        return replace(
            sample,
            ground_speed_m_s=reported_speed,
            velocity_x_m_s=-vector_speed * cos(heading_rad),
            velocity_y_m_s=-vector_speed * sin(heading_rad),
            velocity_z_m_s=(sample.vertical_speed_m_s or 0.0) + 10.0 * intensity,
        )
