"""External source transport protocol."""

from enum import StrEnum


class ExternalTransportProtocol(StrEnum):
    """Supported external source transport protocols."""

    UDP = "udp"
