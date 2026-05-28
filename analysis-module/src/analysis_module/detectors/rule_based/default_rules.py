"""Default rule registration for the analysis module."""

from __future__ import annotations

import re
from collections.abc import Mapping

from analysis_module.detectors.rule_based.rules.battery_drop import BatteryDropRule
from analysis_module.detectors.rule_based.rules.gps_signal_loss import (
    GpsSignalLossRule,
)
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
from analysis_module.domain import TelemetryRule


def create_default_rules(
    enabled_rules: tuple[str, ...] | None = None,
    thresholds: Mapping[str, float] | None = None,
) -> tuple[TelemetryRule, ...]:
    """Create the default deterministic rule set."""

    values = thresholds or {}
    registered_rules: tuple[tuple[str, TelemetryRule], ...] = (
        (
            "gps_signal_loss",
            GpsSignalLossRule(
                min_satellites=int(
                    _threshold(values, "gps_signal_loss.min_satellites", 1)
                ),
                min_fix_type=int(_threshold(values, "gps_signal_loss.min_fix_type", 2)),
            ),
        ),
        (
            "gps_spoofing",
            GpsSpoofingRule(
                max_implied_speed_m_s=_threshold(
                    values,
                    "gps_spoofing.max_implied_speed_m_s",
                    70.0,
                ),
                speed_margin_m_s=_threshold(
                    values,
                    "gps_spoofing.speed_margin_m_s",
                    15.0,
                ),
                min_distance_delta_m=_threshold(
                    values,
                    "gps_spoofing.min_distance_delta_m",
                    50.0,
                ),
            ),
        ),
        (
            "imu_spike",
            ImuSpikeRule(
                max_angular_rate_rad_s=_threshold(
                    values,
                    "imu_spike.max_angular_rate_rad_s",
                    6.0,
                ),
                max_attitude_change_rad_s=_threshold(
                    values,
                    "imu_spike.max_attitude_change_rad_s",
                    5.0,
                ),
            ),
        ),
        (
            "battery_drop",
            BatteryDropRule(
                min_drop_percent=_threshold(values, "battery_drop.min_drop_percent", 5.0),
                max_drop_percent_per_sec=_threshold(
                    values,
                    "battery_drop.max_drop_percent_per_sec",
                    1.0,
                ),
            ),
        ),
        (
            "low_battery",
            LowBatteryRule(
                warning_threshold_percent=_threshold(
                    values,
                    "low_battery.warning_threshold_percent",
                    25.0,
                ),
                critical_threshold_percent=_threshold(
                    values,
                    "low_battery.critical_threshold_percent",
                    15.0,
                ),
            ),
        ),
        (
            "impossible_altitude",
            ImpossibleAltitudeRule(
                min_altitude_m=_threshold(
                    values,
                    "impossible_altitude.min_altitude_m",
                    -500.0,
                ),
                max_altitude_m=_threshold(
                    values,
                    "impossible_altitude.max_altitude_m",
                    30_000.0,
                ),
            ),
        ),
        (
            "telemetry_freeze",
            TelemetryFreezeRule(
                min_elapsed_sec=_threshold(
                    values,
                    "telemetry_freeze.min_elapsed_sec",
                    5.0,
                ),
                position_epsilon_m=_threshold(
                    values,
                    "telemetry_freeze.position_epsilon_m",
                    0.1,
                ),
                value_epsilon=_threshold(values, "telemetry_freeze.value_epsilon", 0.001),
            ),
        ),
        (
            "telemetry_gap",
            TelemetryGapRule(
                max_elapsed_sec=_threshold(
                    values,
                    "telemetry_gap.max_elapsed_sec",
                    10.0,
                ),
            ),
        ),
        (
            "motion_inconsistency",
            MotionInconsistencyRule(
                max_speed_delta_m_s=_threshold(
                    values,
                    "motion_inconsistency.max_speed_delta_m_s",
                    5.0,
                ),
                min_reference_speed_m_s=_threshold(
                    values,
                    "motion_inconsistency.min_reference_speed_m_s",
                    1.0,
                ),
            ),
        ),
    )

    rules = tuple(rule for _, rule in registered_rules)
    if enabled_rules is None:
        return rules

    enabled = {_normalize_rule_name(rule_name) for rule_name in enabled_rules}
    return tuple(
        rule
        for rule_key, rule in registered_rules
        if _rule_enabled(rule_key, rule, enabled)
    )


def _threshold(
    thresholds: Mapping[str, float],
    name: str,
    default: float,
) -> float:
    return float(thresholds.get(name, default))


def _rule_enabled(
    rule_key: str,
    rule: TelemetryRule,
    enabled_rules: set[str],
) -> bool:
    return (
        _normalize_rule_name(rule_key) in enabled_rules
        or _normalize_rule_name(rule.name) in enabled_rules
        or _normalize_rule_name(rule.__class__.__name__) in enabled_rules
    )


def _normalize_rule_name(value: str) -> str:
    value = value.strip().replace("-", "_")
    if value.upper() == value:
        return value.lower()
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"_+", "_", value).lower()
