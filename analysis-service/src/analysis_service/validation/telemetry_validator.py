"""Validation for incoming UnifiedTelemetry payloads."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from analysis_module import UnifiedTelemetry

from analysis_service.validation.validation_errors import (
    TelemetryValidationError,
    TelemetryValidationViolation,
)


_ALTITUDE_MIN_M = -1_000.0
_ALTITUDE_MAX_M = 100_000.0
_ANGLE_MIN_RAD = -math.tau
_ANGLE_MAX_RAD = math.tau


@dataclass(frozen=True, slots=True)
class SchemaLoader:
    """Loads shared telemetry JSON Schema from the repository contract folder."""

    schema_path: Path | None = None

    def load(self) -> dict[str, Any]:
        path = self.schema_path or _find_schema_path()
        return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class JsonSchemaTelemetryValidator:
    """Validates telemetry dictionaries against the shared telemetry schema."""

    schema: Mapping[str, Any]

    @classmethod
    def load_default(cls) -> "JsonSchemaTelemetryValidator":
        return cls(SchemaLoader().load())

    def validate_payload(self, payload: Mapping[str, Any]) -> None:
        violations: list[TelemetryValidationViolation] = []
        properties = self.schema.get("properties", {})
        required = tuple(self.schema.get("required", ()))

        for field_name in required:
            if field_name not in payload:
                violations.append(
                    TelemetryValidationViolation(
                        field=field_name,
                        message="Field is required.",
                    )
                )

        allowed_fields = set(properties)
        extra_fields = sorted(set(payload) - allowed_fields)
        for field_name in extra_fields:
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Field is not defined by telemetry.schema.json.",
                )
            )

        for field_name, value in payload.items():
            field_schema = properties.get(field_name)
            if field_schema is None:
                continue
            self._validate_schema_field(
                field_name,
                value,
                field_schema,
                violations,
            )

        if violations:
            raise TelemetryValidationError(violations)

    def _validate_schema_field(
        self,
        field_name: str,
        value: Any,
        field_schema: Mapping[str, Any],
        violations: list[TelemetryValidationViolation],
    ) -> None:
        expected_type = field_schema.get("type")
        if expected_type == "string":
            self._validate_string(field_name, value, field_schema, violations)
        elif expected_type == "number":
            self._validate_number(field_name, value, field_schema, violations)
        elif expected_type == "integer":
            self._validate_integer(field_name, value, field_schema, violations)
        elif expected_type == "boolean" and not isinstance(value, bool):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Expected boolean value.",
                )
            )

    def _validate_string(
        self,
        field_name: str,
        value: Any,
        field_schema: Mapping[str, Any],
        violations: list[TelemetryValidationViolation],
    ) -> None:
        if not isinstance(value, str):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Expected string value.",
                )
            )
            return

        min_length = field_schema.get("minLength")
        if min_length is not None and len(value) < int(min_length):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message=f"String length must be at least {min_length}.",
                )
            )
        if field_schema.get("format") == "date-time" and not _is_datetime(value):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Expected ISO 8601 date-time value.",
                )
            )

    def _validate_number(
        self,
        field_name: str,
        value: Any,
        field_schema: Mapping[str, Any],
        violations: list[TelemetryValidationViolation],
    ) -> None:
        if not _is_finite_number(value):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Expected finite number.",
                )
            )
            return
        self._validate_bounds(field_name, float(value), field_schema, violations)

    def _validate_integer(
        self,
        field_name: str,
        value: Any,
        field_schema: Mapping[str, Any],
        violations: list[TelemetryValidationViolation],
    ) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Expected integer value.",
                )
            )
            return
        self._validate_bounds(field_name, float(value), field_schema, violations)

    def _validate_bounds(
        self,
        field_name: str,
        value: float,
        field_schema: Mapping[str, Any],
        violations: list[TelemetryValidationViolation],
    ) -> None:
        minimum = field_schema.get("minimum")
        maximum = field_schema.get("maximum")
        if minimum is not None and value < float(minimum):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message=f"Value must be >= {minimum}.",
                )
            )
        if maximum is not None and value > float(maximum):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message=f"Value must be <= {maximum}.",
                )
            )


@dataclass(frozen=True, slots=True)
class UnifiedTelemetryValidator:
    """Validates a UnifiedTelemetry object before analyzer execution."""

    altitude_min_m: float = _ALTITUDE_MIN_M
    altitude_max_m: float = _ALTITUDE_MAX_M

    def validate(self, telemetry: UnifiedTelemetry) -> None:
        violations: list[TelemetryValidationViolation] = []

        self._validate_required_string("drone_id", telemetry.drone_id, violations)
        if not isinstance(telemetry.timestamp, datetime):
            violations.append(
                TelemetryValidationViolation(
                    field="timestamp",
                    message="Expected datetime value.",
                )
            )

        self._validate_number(
            "latitude_deg",
            telemetry.latitude_deg,
            violations,
            minimum=-90.0,
            maximum=90.0,
        )
        self._validate_number(
            "longitude_deg",
            telemetry.longitude_deg,
            violations,
            minimum=-180.0,
            maximum=180.0,
        )
        self._validate_number(
            "altitude_m",
            telemetry.altitude_m,
            violations,
            minimum=self.altitude_min_m,
            maximum=self.altitude_max_m,
        )
        self._validate_number(
            "battery_percent",
            telemetry.battery_percent,
            violations,
            minimum=0.0,
            maximum=100.0,
        )
        self._validate_integer("satellites", telemetry.satellites, violations, minimum=0)

        for field_name in (
            "ground_speed_m_s",
            "gps_eph",
            "gps_epv",
            "battery_voltage_v",
            "battery_current_a",
        ):
            self._validate_optional_number(
                field_name,
                getattr(telemetry, field_name),
                violations,
                minimum=0.0,
            )

        for field_name in (
            "vertical_speed_m_s",
            "relative_altitude_m",
            "velocity_x_m_s",
            "velocity_y_m_s",
            "velocity_z_m_s",
            "roll_rate_rad_s",
            "pitch_rate_rad_s",
            "yaw_rate_rad_s",
        ):
            self._validate_optional_number(
                field_name,
                getattr(telemetry, field_name),
                violations,
            )

        for field_name in ("roll_rad", "pitch_rad", "yaw_rad"):
            self._validate_optional_number(
                field_name,
                getattr(telemetry, field_name),
                violations,
                minimum=_ANGLE_MIN_RAD,
                maximum=_ANGLE_MAX_RAD,
            )

        self._validate_optional_number(
            "heading_deg",
            telemetry.heading_deg,
            violations,
            minimum=0.0,
            maximum=360.0,
        )
        self._validate_optional_integer(
            "satellites_visible",
            telemetry.satellites_visible,
            violations,
            minimum=0,
        )
        self._validate_optional_integer(
            "gps_fix_type",
            telemetry.gps_fix_type,
            violations,
            minimum=0,
            maximum=6,
        )
        self._validate_optional_integer(
            "sensor_health_flags",
            telemetry.sensor_health_flags,
            violations,
            minimum=0,
        )
        for field_name in (
            "attitude_age_ms",
            "position_age_ms",
            "gps_age_ms",
            "system_age_ms",
        ):
            self._validate_optional_integer(
                field_name,
                getattr(telemetry, field_name),
                violations,
                minimum=0,
            )
        self._validate_optional_number(
            "message_quality",
            telemetry.message_quality,
            violations,
            minimum=0.0,
            maximum=1.0,
        )

        if violations:
            raise TelemetryValidationError(violations)

    def _validate_required_string(
        self,
        field_name: str,
        value: Any,
        violations: list[TelemetryValidationViolation],
    ) -> None:
        if not isinstance(value, str) or len(value) == 0:
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Expected non-empty string.",
                )
            )

    def _validate_number(
        self,
        field_name: str,
        value: Any,
        violations: list[TelemetryValidationViolation],
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> None:
        if not _is_finite_number(value):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Expected finite number.",
                )
            )
            return
        self._validate_number_bounds(
            field_name,
            float(value),
            violations,
            minimum=minimum,
            maximum=maximum,
        )

    def _validate_optional_number(
        self,
        field_name: str,
        value: Any,
        violations: list[TelemetryValidationViolation],
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> None:
        if value is None:
            return
        self._validate_number(
            field_name,
            value,
            violations,
            minimum=minimum,
            maximum=maximum,
        )

    def _validate_integer(
        self,
        field_name: str,
        value: Any,
        violations: list[TelemetryValidationViolation],
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message="Expected integer value.",
                )
            )
            return
        self._validate_number_bounds(
            field_name,
            float(value),
            violations,
            minimum=minimum,
            maximum=maximum,
        )

    def _validate_optional_integer(
        self,
        field_name: str,
        value: Any,
        violations: list[TelemetryValidationViolation],
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> None:
        if value is None:
            return
        self._validate_integer(
            field_name,
            value,
            violations,
            minimum=minimum,
            maximum=maximum,
        )

    def _validate_number_bounds(
        self,
        field_name: str,
        value: float,
        violations: list[TelemetryValidationViolation],
        minimum: float | int | None = None,
        maximum: float | int | None = None,
    ) -> None:
        if minimum is not None and value < float(minimum):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message=f"Value must be >= {minimum}.",
                )
            )
        if maximum is not None and value > float(maximum):
            violations.append(
                TelemetryValidationViolation(
                    field=field_name,
                    message=f"Value must be <= {maximum}.",
                )
            )


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    return math.isfinite(float(value))


def _is_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


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
