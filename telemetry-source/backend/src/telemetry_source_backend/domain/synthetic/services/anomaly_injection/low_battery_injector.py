"""Low battery anomaly injector."""

from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class LowBatteryInjector:
    """Decreases battery level according to anomaly intensity."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.LOW_BATTERY

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        battery_percent = max(0.0, 15.0 - intensity * 15.0)
        return replace(
            sample,
            battery_percent=battery_percent,
            battery_voltage_v=10.5 + battery_percent / 100.0 * 2.1,
        )
