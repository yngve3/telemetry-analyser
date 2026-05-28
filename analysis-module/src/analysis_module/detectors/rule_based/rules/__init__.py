"""Default deterministic anomaly rules."""

from analysis_module.detectors.rule_based.rules.battery_drop import BatteryDropRule
from analysis_module.detectors.rule_based.rules.gps_signal_loss import GpsSignalLossRule
from analysis_module.detectors.rule_based.rules.gps_spoofing import GpsSpoofingRule
from analysis_module.detectors.rule_based.rules.imu_spike import ImuSpikeRule
from analysis_module.detectors.rule_based.rules.impossible_altitude import (
    ImpossibleAltitudeRule,
)
from analysis_module.detectors.rule_based.rules.low_battery import LowBatteryRule
from analysis_module.detectors.rule_based.rules.motion_inconsistency import (
    MotionInconsistencyRule,
)
from analysis_module.detectors.rule_based.rules.telemetry_freeze import (
    TelemetryFreezeRule,
)
from analysis_module.detectors.rule_based.rules.telemetry_gap import TelemetryGapRule

__all__ = [
    "BatteryDropRule",
    "GpsSignalLossRule",
    "GpsSpoofingRule",
    "ImuSpikeRule",
    "ImpossibleAltitudeRule",
    "LowBatteryRule",
    "MotionInconsistencyRule",
    "TelemetryFreezeRule",
    "TelemetryGapRule",
]
