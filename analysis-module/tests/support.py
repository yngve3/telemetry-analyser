from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import sys

ANALYSIS_MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANALYSIS_MODULE_ROOT / "src"))

from analysis_module import UnifiedTelemetry  # noqa: E402


def telemetry(**overrides: object) -> UnifiedTelemetry:
    values: dict[str, Any] = {
        "timestamp": datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
        "drone_id": "uav-001",
        "latitude_deg": 55.7558,
        "longitude_deg": 37.6173,
        "altitude_m": 120.0,
        "battery_percent": 80.0,
        "satellites": 10,
        "ground_speed_m_s": 12.5,
        "vertical_speed_m_s": 0.2,
        "heading_deg": 180.0,
        "relative_altitude_m": 120.0,
        "velocity_x_m_s": 12.5,
        "velocity_y_m_s": 0.0,
        "velocity_z_m_s": 0.2,
        "roll_rad": 0.0,
        "pitch_rad": 0.0,
        "yaw_rad": 3.14159,
        "roll_rate_rad_s": 0.1,
        "pitch_rate_rad_s": 0.1,
        "yaw_rate_rad_s": 0.1,
        "satellites_visible": 10,
        "gps_fix_type": 3,
        "gps_eph": 100.0,
        "gps_epv": 150.0,
        "battery_voltage_v": 12.2,
    }
    values.update(overrides)
    return UnifiedTelemetry(**values)


def seconds_after(seconds: float) -> datetime:
    return telemetry().timestamp + timedelta(seconds=seconds)
