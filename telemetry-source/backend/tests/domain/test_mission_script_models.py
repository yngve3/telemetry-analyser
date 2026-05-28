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
    TurnDirection,
)


class MissionScriptModelsTest(unittest.TestCase):
    def test_mission_script_can_represent_human_friendly_steps(self) -> None:
        script = MissionScript(
            name="simple_mission",
            frequency_hz=20.0,
            home=ScriptHome(
                latitude=47.397742,
                longitude=8.545594,
                heading_deg=0.0,
            ),
            steps=(
                ScriptStep(
                    type=ScriptStepType.TAKEOFF,
                    target_altitude=30.0,
                ),
                ScriptStep(
                    type=ScriptStepType.MOVE_FORWARD,
                    distance_m=100.0,
                    speed_m_s=8.0,
                ),
                ScriptStep(
                    type=ScriptStepType.TURN,
                    direction=TurnDirection.RIGHT,
                    angle_deg=90.0,
                ),
            ),
        )

        self.assertEqual(script.name, "simple_mission")
        self.assertEqual(script.steps[1].distance_m, 100.0)
        self.assertEqual(script.steps[2].direction, TurnDirection.RIGHT)


if __name__ == "__main__":
    unittest.main()

