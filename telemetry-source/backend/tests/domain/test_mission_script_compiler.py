from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.domain.exceptions import MissionValidationError  # noqa: E402
from telemetry_source_backend.domain.synthetic.models import PhaseType  # noqa: E402
from telemetry_source_backend.domain.synthetic.script.models import (  # noqa: E402
    MissionScript,
    ScriptHome,
    ScriptStep,
    ScriptStepType,
    TurnDirection,
)
from telemetry_source_backend.domain.synthetic.script.services import (  # noqa: E402
    MissionScriptCompiler,
    MissionScriptValidator,
)


class MissionScriptCompilerTest(unittest.TestCase):
    def test_compiles_human_friendly_script_to_executable_phases(self) -> None:
        script = self._script()

        plan = MissionScriptCompiler().compile(script)

        self.assertEqual(plan.name, "simple_mission")
        self.assertEqual(plan.frequency_hz, 20.0)
        self.assertEqual(
            [phase.type for phase in plan.phases],
            [
                PhaseType.TAKEOFF,
                PhaseType.WAYPOINT,
                PhaseType.TURN,
                PhaseType.WAYPOINT,
                PhaseType.HOVER,
                PhaseType.RETURN_HOME,
                PhaseType.LANDING,
            ],
        )
        self.assertAlmostEqual(plan.phases[0].duration_sec, 10.0)
        self.assertAlmostEqual(plan.phases[2].target_heading_deg, 90.0)
        self.assertAlmostEqual(plan.phases[-1].target_altitude, 0.0)

    def test_validator_rejects_invalid_move_forward_step(self) -> None:
        script = MissionScript(
            name="invalid",
            frequency_hz=20.0,
            home=ScriptHome(latitude=47.397742, longitude=8.545594),
            steps=(
                ScriptStep(
                    type=ScriptStepType.MOVE_FORWARD,
                    distance_m=100.0,
                ),
            ),
        )

        with self.assertRaises(MissionValidationError):
            MissionScriptValidator().validate(script)

    def _script(self) -> MissionScript:
        return MissionScript(
            name="simple_mission",
            frequency_hz=20.0,
            home=ScriptHome(
                latitude=47.397742,
                longitude=8.545594,
                altitude=0.0,
                heading_deg=0.0,
                battery=100.0,
            ),
            steps=(
                ScriptStep(type=ScriptStepType.TAKEOFF, target_altitude=30.0),
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
                ScriptStep(
                    type=ScriptStepType.MOVE_FORWARD,
                    distance_m=80.0,
                    speed_m_s=8.0,
                ),
                ScriptStep(type=ScriptStepType.HOVER, duration_sec=10.0),
                ScriptStep(type=ScriptStepType.RETURN_HOME),
                ScriptStep(type=ScriptStepType.LANDING),
            ),
        )


if __name__ == "__main__":
    unittest.main()

