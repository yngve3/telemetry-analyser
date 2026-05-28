from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.domain.synthetic.script.models import (  # noqa: E402
    MissionScript,
    ScriptHome,
    ScriptStep,
    ScriptStepType,
)
from telemetry_source_backend.domain.synthetic.script.services import (  # noqa: E402
    MissionScriptCompiler,
)
from telemetry_source_backend.infrastructure.sources.synthetic_source import (  # noqa: E402
    SyntheticTelemetrySource,
)


class SyntheticTelemetrySourceTest(unittest.IsolatedAsyncioTestCase):
    async def test_read_returns_generated_telemetry_sample(self) -> None:
        plan = MissionScriptCompiler().compile(
            MissionScript(
                name="takeoff",
                frequency_hz=20.0,
                home=ScriptHome(latitude=47.397742, longitude=8.545594),
                steps=(
                    ScriptStep(type=ScriptStepType.TAKEOFF, target_altitude=30.0),
                ),
            )
        )
        source = SyntheticTelemetrySource(plan)

        sample = await source.read()

        self.assertEqual(sample.drone_id, "uav-001")
        self.assertGreater(sample.altitude_m, 0.0)


if __name__ == "__main__":
    unittest.main()

