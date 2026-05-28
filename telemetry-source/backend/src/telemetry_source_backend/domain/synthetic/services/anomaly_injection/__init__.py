"""Synthetic anomaly injection strategies."""

from telemetry_source_backend.domain.synthetic.services.anomaly_injection.anomalous_behavior_injector import (
    AnomalousBehaviorInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.anomaly_injector import (
    AnomalyInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.battery_drop_injector import (
    BatteryDropInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.gps_signal_loss_injector import (
    GpsSignalLossInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.gps_spoofing_injector import (
    GpsSpoofingInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.impossible_altitude_injector import (
    ImpossibleAltitudeInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.imu_spike_injector import (
    ImuSpikeInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.low_battery_injector import (
    LowBatteryInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.motion_inconsistency_injector import (
    MotionInconsistencyInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.telemetry_freeze_injector import (
    TelemetryFreezeInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.telemetry_gap_injector import (
    TelemetryGapInjector,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection.registry import (
    AnomalyInjectorRegistry,
    default_anomaly_registry,
)

__all__ = [
    "AnomalousBehaviorInjector",
    "AnomalyInjector",
    "AnomalyInjectorRegistry",
    "BatteryDropInjector",
    "GpsSignalLossInjector",
    "GpsSpoofingInjector",
    "ImpossibleAltitudeInjector",
    "ImuSpikeInjector",
    "LowBatteryInjector",
    "MotionInconsistencyInjector",
    "TelemetryFreezeInjector",
    "TelemetryGapInjector",
    "default_anomaly_registry",
]
