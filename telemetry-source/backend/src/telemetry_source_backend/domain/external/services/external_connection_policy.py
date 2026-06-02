"""External source connection policy."""

from telemetry_source_backend.domain.exceptions import SourceConfigurationError
from telemetry_source_backend.domain.external.models import (
    ExternalSourceConfig,
    ExternalTransportProtocol,
)


class ExternalConnectionPolicy:
    """Defines connection rules for external telemetry sources."""

    def validate(self, config: ExternalSourceConfig) -> None:
        if not config.name.strip():
            raise SourceConfigurationError("External source name must not be empty.")
        if not config.address.strip():
            raise SourceConfigurationError("External source address must not be empty.")
        if not 1 <= config.port <= 65535:
            raise SourceConfigurationError("External source port must be in 1..65535.")
        if config.protocol is not ExternalTransportProtocol.UDP:
            raise SourceConfigurationError("Only UDP external sources are supported.")
        if config.forward_enabled:
            if not config.forward_host.strip():
                raise SourceConfigurationError("Forward host must not be empty.")
            if not 1 <= config.forward_port <= 65535:
                raise SourceConfigurationError("Forward port must be in 1..65535.")
