"""Mission script validation service."""

from telemetry_source_backend.domain.exceptions import MissionValidationError
from telemetry_source_backend.domain.synthetic.script.models import MissionScript
from telemetry_source_backend.domain.synthetic.script.models import ScriptStep
from telemetry_source_backend.domain.synthetic.script.models import ScriptStepType


class MissionScriptValidator:
    """Validates human-authored mission scripts before compilation."""

    def validate(self, script: MissionScript) -> None:
        if script.frequency_hz <= 0:
            raise MissionValidationError("Mission frequency must be greater than zero.")

        if not script.steps:
            raise MissionValidationError("Mission script must contain at least one step.")

        if not -90 <= script.home.latitude <= 90:
            raise MissionValidationError("Home latitude must be within [-90, 90].")

        if not -180 <= script.home.longitude <= 180:
            raise MissionValidationError("Home longitude must be within [-180, 180].")

        if not 0 <= script.home.battery <= 100:
            raise MissionValidationError("Initial battery must be within [0, 100].")

        for index, step in enumerate(script.steps, start=1):
            self._validate_step(index, step)

    def _validate_step(self, index: int, step: ScriptStep) -> None:
        match step.type:
            case ScriptStepType.TAKEOFF:
                self._require_positive(index, "target_altitude", step.target_altitude)
            case ScriptStepType.MOVE_FORWARD:
                self._require_positive(index, "distance_m", step.distance_m)
                self._require_positive(index, "speed_m_s", step.speed_m_s)
            case ScriptStepType.TURN:
                if step.direction is None:
                    raise MissionValidationError(
                        f"Step {index}: turn direction is required."
                    )
                self._require_positive(index, "angle_deg", step.angle_deg)
            case ScriptStepType.HOVER:
                self._require_positive(index, "duration_sec", step.duration_sec)
            case ScriptStepType.RETURN_HOME:
                if step.speed_m_s is not None:
                    self._require_positive(index, "speed_m_s", step.speed_m_s)
            case ScriptStepType.LANDING:
                pass

    def _require_positive(
        self,
        index: int,
        field_name: str,
        value: float | None,
    ) -> None:
        if value is None or value <= 0:
            raise MissionValidationError(
                f"Step {index}: {field_name} must be greater than zero."
            )
