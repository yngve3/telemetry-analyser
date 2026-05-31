"""Telemetry shared-contract serialization and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from telemetry_source_backend.domain.common.models import TelemetrySample


class TelemetryContractValidationError(ValueError):
    """Raised when a telemetry sample violates the shared contract."""


def telemetry_sample_to_contract_dict(sample: TelemetrySample) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": sample.timestamp.isoformat(),
        "drone_id": sample.drone_id,
        "latitude_deg": sample.latitude_deg,
        "longitude_deg": sample.longitude_deg,
        "altitude_m": sample.altitude_m,
        "battery_percent": sample.battery_percent,
        "satellites": sample.satellites,
    }

    optional_values = {
        "ground_speed_m_s": sample.ground_speed_m_s,
        "vertical_speed_m_s": sample.vertical_speed_m_s,
        "heading_deg": sample.heading_deg,
        "relative_altitude_m": sample.relative_altitude_m,
        "velocity_x_m_s": sample.velocity_x_m_s,
        "velocity_y_m_s": sample.velocity_y_m_s,
        "velocity_z_m_s": sample.velocity_z_m_s,
        "roll_rad": sample.roll_rad,
        "pitch_rad": sample.pitch_rad,
        "yaw_rad": sample.yaw_rad,
        "roll_rate_rad_s": sample.roll_rate_rad_s,
        "pitch_rate_rad_s": sample.pitch_rate_rad_s,
        "yaw_rate_rad_s": sample.yaw_rate_rad_s,
        "satellites_visible": sample.satellites_visible,
        "gps_fix_type": sample.gps_fix_type,
        "gps_eph": sample.gps_eph,
        "gps_epv": sample.gps_epv,
        "battery_voltage_v": sample.battery_voltage_v,
        "battery_current_a": sample.battery_current_a,
        "system_status": sample.system_status,
        "flight_mode": sample.flight_mode,
        "armed": sample.armed,
        "sensor_health_flags": sample.sensor_health_flags,
        "attitude_age_ms": sample.attitude_age_ms,
        "position_age_ms": sample.position_age_ms,
        "gps_age_ms": sample.gps_age_ms,
        "system_age_ms": sample.system_age_ms,
        "message_quality": sample.message_quality,
    }
    payload.update(
        {
            key: value
            for key, value in optional_values.items()
            if value is not None
        }
    )
    return payload


@dataclass(frozen=True, slots=True)
class TelemetryContractValidator:
    """Small validator for the repository telemetry JSON Schema."""

    schema: dict[str, Any]

    @classmethod
    def load_default(cls) -> "TelemetryContractValidator":
        schema_path = _find_schema_path()
        return cls(json.loads(schema_path.read_text(encoding="utf-8")))

    def validate_sample(self, sample: TelemetrySample) -> None:
        self.validate_payload(telemetry_sample_to_contract_dict(sample))

    def validate_payload(self, payload: dict[str, Any]) -> None:
        required = self.schema.get("required", [])
        for key in required:
            if key not in payload:
                raise TelemetryContractValidationError(
                    f"Telemetry payload is missing required field {key!r}."
                )

        allowed = set(self.schema.get("properties", {}).keys())
        extra = set(payload.keys()) - allowed
        if extra:
            raise TelemetryContractValidationError(
                f"Telemetry payload contains unsupported fields: {sorted(extra)}."
            )

        self._validate_string(payload, "timestamp", min_length=1)
        self._validate_string(payload, "drone_id", min_length=1)
        self._validate_number(payload, "latitude_deg", minimum=-90, maximum=90)
        self._validate_number(payload, "longitude_deg", minimum=-180, maximum=180)
        self._validate_number(payload, "altitude_m")
        self._validate_number(payload, "battery_percent", minimum=0, maximum=100)
        self._validate_integer(payload, "satellites", minimum=0)
        self._validate_number(payload, "ground_speed_m_s", minimum=0, required=False)
        self._validate_number(payload, "vertical_speed_m_s", required=False)
        self._validate_number(payload, "heading_deg", minimum=0, maximum=360, required=False)
        self._validate_number(payload, "relative_altitude_m", required=False)
        self._validate_number(payload, "velocity_x_m_s", required=False)
        self._validate_number(payload, "velocity_y_m_s", required=False)
        self._validate_number(payload, "velocity_z_m_s", required=False)
        self._validate_number(payload, "roll_rad", required=False)
        self._validate_number(payload, "pitch_rad", required=False)
        self._validate_number(payload, "yaw_rad", required=False)
        self._validate_number(payload, "roll_rate_rad_s", required=False)
        self._validate_number(payload, "pitch_rate_rad_s", required=False)
        self._validate_number(payload, "yaw_rate_rad_s", required=False)
        self._validate_integer(payload, "satellites_visible", minimum=0, required=False)
        self._validate_integer(payload, "gps_fix_type", minimum=0, maximum=6, required=False)
        self._validate_number(payload, "gps_eph", minimum=0, required=False)
        self._validate_number(payload, "gps_epv", minimum=0, required=False)
        self._validate_number(payload, "battery_voltage_v", minimum=0, required=False)
        self._validate_number(payload, "battery_current_a", minimum=0, required=False)
        self._validate_string(payload, "system_status", min_length=1, required=False)
        self._validate_string(payload, "flight_mode", min_length=1, required=False)
        self._validate_boolean(payload, "armed", required=False)
        self._validate_integer(payload, "sensor_health_flags", minimum=0, required=False)
        self._validate_integer(payload, "attitude_age_ms", minimum=0, required=False)
        self._validate_integer(payload, "position_age_ms", minimum=0, required=False)
        self._validate_integer(payload, "gps_age_ms", minimum=0, required=False)
        self._validate_integer(payload, "system_age_ms", minimum=0, required=False)
        self._validate_number(payload, "message_quality", minimum=0, maximum=1, required=False)

    def _validate_string(
        self,
        payload: dict[str, Any],
        key: str,
        min_length: int = 0,
        required: bool = True,
    ) -> None:
        if key not in payload:
            if required:
                raise TelemetryContractValidationError(
                    f"Telemetry field {key!r} is required."
                )
            return

        value = payload[key]
        if not isinstance(value, str) or len(value) < min_length:
            raise TelemetryContractValidationError(
                f"Telemetry field {key!r} must be a string."
            )

    def _validate_number(
        self,
        payload: dict[str, Any],
        key: str,
        minimum: float | None = None,
        maximum: float | None = None,
        required: bool = True,
    ) -> None:
        if key not in payload:
            if required:
                raise TelemetryContractValidationError(
                    f"Telemetry field {key!r} is required."
                )
            return

        value = payload[key]
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise TelemetryContractValidationError(
                f"Telemetry field {key!r} must be a number."
            )
        if minimum is not None and value < minimum:
            raise TelemetryContractValidationError(
                f"Telemetry field {key!r} must be >= {minimum}."
            )
        if maximum is not None and value > maximum:
            raise TelemetryContractValidationError(
                f"Telemetry field {key!r} must be <= {maximum}."
            )

    def _validate_integer(
        self,
        payload: dict[str, Any],
        key: str,
        minimum: int | None = None,
        maximum: int | None = None,
        required: bool = True,
    ) -> None:
        if key not in payload:
            if required:
                raise TelemetryContractValidationError(
                    f"Telemetry field {key!r} is required."
                )
            return

        value = payload[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise TelemetryContractValidationError(
                f"Telemetry field {key!r} must be an integer."
            )
        if minimum is not None and value < minimum:
            raise TelemetryContractValidationError(
                f"Telemetry field {key!r} must be >= {minimum}."
            )
        if maximum is not None and value > maximum:
            raise TelemetryContractValidationError(
                f"Telemetry field {key!r} must be <= {maximum}."
            )

    def _validate_boolean(
        self,
        payload: dict[str, Any],
        key: str,
        required: bool = True,
    ) -> None:
        if key not in payload:
            if required:
                raise TelemetryContractValidationError(
                    f"Telemetry field {key!r} is required."
                )
            return

        if not isinstance(payload[key], bool):
            raise TelemetryContractValidationError(
                f"Telemetry field {key!r} must be a boolean."
            )


def _find_schema_path() -> Path:
    current = Path(__file__).resolve()
    candidates = [
        parent / "shared-contracts" / "telemetry.schema.json"
        for parent in current.parents
    ]
    candidates.append(Path("/app/shared-contracts/telemetry.schema.json"))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("shared-contracts/telemetry.schema.json was not found.")
