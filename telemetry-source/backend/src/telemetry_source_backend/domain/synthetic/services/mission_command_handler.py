"""Synthetic mission command handler."""

from telemetry_source_backend.domain.exceptions import MissionCommandError
from telemetry_source_backend.domain.synthetic.models import (
    AnomalyProfile,
    AnomalyType,
    CommandType,
    MissionCommand,
    MissionRuntimeState,
    ScheduledAnomaly,
)


class MissionCommandHandler:
    """Applies runtime commands to mission state."""

    allowed_parameters = frozenset(
        {
            "target_speed",
            "frequency_hz",
            "flight_mode",
            "target_altitude",
        }
    )

    def handle(
        self,
        state: MissionRuntimeState,
        command: MissionCommand,
    ) -> None:
        match command.command:
            case CommandType.INJECT_ANOMALY:
                self._inject_anomaly(state, command)
            case CommandType.SET_PARAMETER:
                self._set_parameter(state, command)
            case CommandType.PAUSE:
                state.is_running = False
            case CommandType.RESUME:
                state.is_running = True
            case CommandType.STOP:
                state.is_running = False
                state.elapsed_sec = 0.0

    def _inject_anomaly(
        self,
        state: MissionRuntimeState,
        command: MissionCommand,
    ) -> None:
        anomaly_type = command.parameters.get("type")
        start_after_sec = float(command.parameters.get("start_after_sec", 0.0))
        duration_sec = float(command.parameters.get("duration_sec", 0.0))
        intensity = float(command.parameters.get("intensity", 1.0))

        if duration_sec <= 0:
            raise MissionCommandError("Anomaly duration must be greater than zero.")

        state.scheduled_anomalies.append(
            ScheduledAnomaly(
                profile=AnomalyProfile(
                    anomaly_type=AnomalyType(str(anomaly_type)),
                    intensity=intensity,
                ),
                start_sec=state.elapsed_sec + max(start_after_sec, 0.0),
                duration_sec=duration_sec,
            )
        )

    def _set_parameter(
        self,
        state: MissionRuntimeState,
        command: MissionCommand,
    ) -> None:
        name = command.parameters.get("name")
        if not isinstance(name, str) or name not in self.allowed_parameters:
            raise MissionCommandError(f"Unsupported mission parameter: {name!r}.")

        state.parameter_overrides[name] = command.parameters.get("value")
