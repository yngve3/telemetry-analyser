"""Validation errors raised for invalid telemetry input."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TelemetryValidationViolation:
    """Single telemetry validation failure."""

    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "message": self.message,
        }


class TelemetryValidationError(ValueError):
    """Raised when telemetry violates the accepted input contract."""

    def __init__(self, violations: list[TelemetryValidationViolation]) -> None:
        self.violations = tuple(violations)
        message = "; ".join(
            f"{violation.field}: {violation.message}"
            for violation in self.violations
        )
        super().__init__(message or "Telemetry payload is invalid.")

    def to_detail(self) -> list[dict[str, str]]:
        return [violation.to_dict() for violation in self.violations]
