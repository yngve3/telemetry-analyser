"""Battery drop anomaly injector."""

from dataclasses import replace

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import AnomalyProfile, AnomalyType


class BatteryDropInjector:
    """Applies a sharp battery charge and voltage drop."""

    @property
    def anomaly_type(self) -> AnomalyType:
        return AnomalyType.BATTERY_DROP

    def apply(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        intensity = min(max(profile.intensity, 0.0), 1.0)
        voltage = sample.battery_voltage_v if sample.battery_voltage_v is not None else 12.0
        return replace(
            sample,
            battery_percent=max(0.0, sample.battery_percent - 35.0 - 45.0 * intensity),
            battery_voltage_v=max(0.0, voltage - 1.5 - 3.0 * intensity),
            battery_current_a=(sample.battery_current_a or 0.0) + 20.0 * intensity,
        )
