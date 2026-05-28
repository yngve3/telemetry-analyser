from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.domain.exceptions import SourceConfigurationError  # noqa: E402
from telemetry_source_backend.domain.external.models import (  # noqa: E402
    ExternalSourceConfig,
    ExternalTransportProtocol,
)
from telemetry_source_backend.domain.external.services import (  # noqa: E402
    ExternalConnectionPolicy,
)


class ExternalConnectionPolicyTest(unittest.TestCase):
    def test_valid_udp_config_is_accepted(self) -> None:
        ExternalConnectionPolicy().validate(
            ExternalSourceConfig(
                name="mavlink_udp",
                address="127.0.0.1",
                port=14550,
                protocol=ExternalTransportProtocol.UDP,
            )
        )

    def test_invalid_port_is_rejected(self) -> None:
        with self.assertRaises(SourceConfigurationError):
            ExternalConnectionPolicy().validate(
                ExternalSourceConfig(
                    name="mavlink_udp",
                    address="127.0.0.1",
                    port=0,
                    protocol=ExternalTransportProtocol.UDP,
                )
            )


if __name__ == "__main__":
    unittest.main()
