"""Domain exceptions."""


class TelemetrySourceDomainError(Exception):
    """Base error for telemetry source domain rules."""


class MissionValidationError(TelemetrySourceDomainError):
    """Raised when a synthetic mission definition is invalid."""


class MissionCommandError(TelemetrySourceDomainError):
    """Raised when a synthetic mission command is invalid."""


class SourceConfigurationError(TelemetrySourceDomainError):
    """Raised when a telemetry source configuration is invalid."""
