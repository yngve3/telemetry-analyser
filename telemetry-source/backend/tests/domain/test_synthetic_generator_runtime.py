from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from telemetry_source_backend.domain.synthetic.models import (  # noqa: E402
    CommandType,
    MissionCommand,
)
from telemetry_source_backend.domain.synthetic.script.models import (  # noqa: E402
    MissionScript,
    ScriptHome,
    ScriptStep,
    ScriptStepType,
)
from telemetry_source_backend.domain.synthetic.script.services import (  # noqa: E402
    MissionScriptCompiler,
)
from telemetry_source_backend.domain.synthetic.services import geodesy  # noqa: E402
from telemetry_source_backend.domain.synthetic.services.mission_runner import (  # noqa: E402
    MissionRunner,
)
from telemetry_source_backend.domain.synthetic.services.motion_profile_solver import (  # noqa: E402
    MotionProfileSolver,
)
from telemetry_source_backend.domain.synthetic.services.synthetic_telemetry_factory import (  # noqa: E402
    SyntheticTelemetryFactory,
)


class SyntheticGeneratorRuntimeTest(unittest.TestCase):
    def test_factory_generates_takeoff_sample_by_elapsed_time(self) -> None:
        plan = MissionScriptCompiler().compile(self._takeoff_script())

        sample = SyntheticTelemetryFactory().create_sample(
            plan,
            elapsed_sec=5.0,
            timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
        )

        self.assertAlmostEqual(sample.altitude_m, 15.0)
        self.assertEqual(sample.drone_id, "uav-001")
        self.assertEqual(sample.satellites, 10)

    def test_runner_applies_runtime_anomaly_command_only_in_active_window(self) -> None:
        plan = MissionScriptCompiler().compile(self._takeoff_script())
        runner = MissionRunner(plan)
        runner.start()
        runner.submit_command(
            MissionCommand(
                command=CommandType.INJECT_ANOMALY,
                parameters={
                    "type": "GPS_SPOOFING",
                    "start_after_sec": 1,
                    "duration_sec": 2,
                    "intensity": 1.0,
                },
            )
        )

        before = runner.sample()
        active = runner.tick(1.0)
        runner.tick(2.0)
        after = runner.sample()

        self.assertAlmostEqual(before.latitude_deg, plan.initial_state.latitude)
        self.assertGreater(active.latitude_deg, before.latitude_deg)
        self.assertLess(after.latitude_deg - before.latitude_deg, 0.0001)

    def test_runner_set_parameter_recalculates_future_phase_duration(self) -> None:
        plan = MissionScriptCompiler().compile(
            MissionScript(
                name="move",
                frequency_hz=20.0,
                home=ScriptHome(latitude=47.397742, longitude=8.545594),
                steps=(
                    ScriptStep(type=ScriptStepType.TAKEOFF, target_altitude=30.0),
                    ScriptStep(
                        type=ScriptStepType.MOVE_FORWARD,
                        distance_m=100.0,
                        speed_m_s=8.0,
                    ),
                ),
            )
        )
        runner = MissionRunner(plan)
        runner.start()
        runner.submit_command(
            MissionCommand(
                command=CommandType.SET_PARAMETER,
                parameters={"name": "target_speed", "value": 12.0},
            )
        )

        runner.tick(10.0)
        sample = runner.tick(1.0)

        self.assertEqual(sample.ground_speed_m_s, 12.0)
        self.assertIn(1, runner.state.phase_duration_overrides)
        self.assertLess(
            runner.state.phase_duration_overrides[1],
            plan.phases[1].duration_sec,
        )

    def test_runner_set_parameter_recalculates_active_phase_duration(self) -> None:
        plan = MissionScriptCompiler().compile(
            MissionScript(
                name="move",
                frequency_hz=20.0,
                home=ScriptHome(latitude=47.397742, longitude=8.545594),
                steps=(
                    ScriptStep(
                        type=ScriptStepType.MOVE_FORWARD,
                        distance_m=100.0,
                        speed_m_s=8.0,
                    ),
                ),
            )
        )
        runner = MissionRunner(plan)
        runner.start()
        before = runner.tick(4.0)
        phase = plan.phases[0]
        remaining_distance_m = geodesy.distance(
            before.latitude_deg,
            before.longitude_deg,
            phase.target_latitude,
            phase.target_longitude,
        )

        runner.submit_command(
            MissionCommand(
                command=CommandType.SET_PARAMETER,
                parameters={"name": "target_speed", "value": 4.0},
            )
        )
        sample = runner.sample()

        expected_duration = 4.0 + MotionProfileSolver().duration_for_distance(
            remaining_distance_m,
            4.0,
            plan.motion_profile.horizontal_acceleration_m_s2,
        )
        self.assertEqual(sample.ground_speed_m_s, 4.0)
        self.assertAlmostEqual(
            runner.state.phase_duration_overrides[0],
            expected_duration,
            places=6,
        )

    def _takeoff_script(self) -> MissionScript:
        return MissionScript(
            name="takeoff",
            frequency_hz=20.0,
            home=ScriptHome(latitude=47.397742, longitude=8.545594),
            steps=(ScriptStep(type=ScriptStepType.TAKEOFF, target_altitude=30.0),),
        )


if __name__ == "__main__":
    unittest.main()
