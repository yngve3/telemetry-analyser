"""Domain service for creating synthetic telemetry samples."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import cos, radians, sin
from typing import Iterable

from telemetry_source_backend.domain.common.models import TelemetrySample
from telemetry_source_backend.domain.synthetic.models import (
    AnomalyProfile,
    MissionPlan,
    PhaseType,
)
from telemetry_source_backend.domain.synthetic.services.anomaly_injection import (
    AnomalyInjectorRegistry,
    default_anomaly_registry,
)
from telemetry_source_backend.domain.synthetic.services.mission_interpolator import (
    MissionInterpolator,
)
from telemetry_source_backend.domain.synthetic.services.telemetry_noise_model import (
    TelemetryNoiseModel,
)


@dataclass(frozen=True, slots=True)
class SyntheticTelemetryFactory:
    """Creates telemetry samples from a synthetic mission plan."""

    anomaly_registry: AnomalyInjectorRegistry = field(
        default_factory=default_anomaly_registry
    )
    interpolator: MissionInterpolator = field(default_factory=MissionInterpolator)
    noise_model: TelemetryNoiseModel = field(default_factory=TelemetryNoiseModel)

    def create_sample(
        self,
        mission_plan: MissionPlan,
        elapsed_sec: float = 0.0,
        active_anomalies: Iterable[AnomalyProfile] = (),
        timestamp: datetime | None = None,
        duration_overrides: dict[int, float] | None = None,
        speed_overrides: dict[int, float] | None = None,
    ) -> TelemetrySample:
        state = self.interpolator.interpolate(
            mission_plan,
            elapsed_sec,
            duration_overrides,
            speed_overrides,
        )
        sample = TelemetrySample(
            timestamp=timestamp or datetime.now(tz=UTC),
            drone_id=mission_plan.drone_id,
            latitude_deg=state.latitude,
            longitude_deg=state.longitude,
            altitude_m=state.altitude,
            battery_percent=state.battery,
            satellites=10,
            ground_speed_m_s=state.ground_speed_m_s,
            vertical_speed_m_s=state.vertical_speed_m_s,
            heading_deg=state.heading_deg,
        )
        sample = self._with_derived_telemetry(
            mission_plan,
            sample,
            active_phase_index=state.active_phase_index,
            duration_overrides=duration_overrides,
        )
        sample = self.noise_model.apply(
            sample,
            mission_plan.noise_profile,
            elapsed_sec,
        )

        for anomaly in active_anomalies:
            sample = self.apply_anomaly(sample, anomaly)

        return self._with_derived_telemetry(
            mission_plan,
            sample,
            active_phase_index=state.active_phase_index,
            duration_overrides=duration_overrides,
        )

    def apply_anomaly(
        self,
        sample: TelemetrySample,
        profile: AnomalyProfile,
    ) -> TelemetrySample:
        injector = self.anomaly_registry.get(profile.anomaly_type)
        return injector.apply(sample, profile)

    def _with_derived_telemetry(
        self,
        mission_plan: MissionPlan,
        sample: TelemetrySample,
        active_phase_index: int,
        duration_overrides: dict[int, float] | None,
    ) -> TelemetrySample:
        heading_deg = sample.heading_deg or 0.0
        heading_rad = radians(heading_deg)
        ground_speed = sample.ground_speed_m_s or 0.0
        vertical_speed = sample.vertical_speed_m_s or 0.0
        yaw_rate = self._yaw_rate_rad_s(
            mission_plan,
            active_phase_index,
            duration_overrides,
        )
        velocity_x = ground_speed * cos(heading_rad)
        velocity_y = ground_speed * sin(heading_rad)
        velocity_z = vertical_speed
        roll = self._clamp(yaw_rate * 0.5, -0.35, 0.35)
        pitch = self._clamp(vertical_speed * 0.03, -0.2, 0.2)

        return TelemetrySample(
            timestamp=sample.timestamp,
            drone_id=sample.drone_id,
            latitude_deg=sample.latitude_deg,
            longitude_deg=sample.longitude_deg,
            altitude_m=sample.altitude_m,
            battery_percent=sample.battery_percent,
            satellites=sample.satellites,
            ground_speed_m_s=sample.ground_speed_m_s,
            vertical_speed_m_s=sample.vertical_speed_m_s,
            heading_deg=sample.heading_deg,
            relative_altitude_m=sample.altitude_m
            - mission_plan.initial_state.altitude,
            velocity_x_m_s=sample.velocity_x_m_s
            if sample.velocity_x_m_s is not None
            else velocity_x,
            velocity_y_m_s=sample.velocity_y_m_s
            if sample.velocity_y_m_s is not None
            else velocity_y,
            velocity_z_m_s=sample.velocity_z_m_s
            if sample.velocity_z_m_s is not None
            else velocity_z,
            roll_rad=sample.roll_rad if sample.roll_rad is not None else roll,
            pitch_rad=sample.pitch_rad if sample.pitch_rad is not None else pitch,
            yaw_rad=sample.yaw_rad if sample.yaw_rad is not None else heading_rad,
            roll_rate_rad_s=sample.roll_rate_rad_s or 0.0,
            pitch_rate_rad_s=sample.pitch_rate_rad_s or 0.0,
            yaw_rate_rad_s=sample.yaw_rate_rad_s
            if sample.yaw_rate_rad_s is not None
            else yaw_rate,
            satellites_visible=sample.satellites_visible
            if sample.satellites_visible is not None
            else sample.satellites,
            gps_fix_type=sample.gps_fix_type
            if sample.gps_fix_type is not None
            else (3 if sample.satellites > 0 else 1),
            gps_eph=sample.gps_eph if sample.gps_eph is not None else 100.0,
            gps_epv=sample.gps_epv if sample.gps_epv is not None else 150.0,
            battery_voltage_v=sample.battery_voltage_v
            if sample.battery_voltage_v is not None
            else self._battery_voltage(sample.battery_percent),
            battery_current_a=sample.battery_current_a
            if sample.battery_current_a is not None
            else self._battery_current(ground_speed, vertical_speed),
            system_status=sample.system_status or "active",
            flight_mode=sample.flight_mode or "auto",
            armed=True if sample.armed is None else sample.armed,
            sensor_health_flags=sample.sensor_health_flags
            if sample.sensor_health_flags is not None
            else 0xFFFFFFFF,
            attitude_age_ms=sample.attitude_age_ms,
            position_age_ms=sample.position_age_ms,
            gps_age_ms=sample.gps_age_ms,
            system_age_ms=sample.system_age_ms,
            message_quality=sample.message_quality,
        )

    def _yaw_rate_rad_s(
        self,
        mission_plan: MissionPlan,
        active_phase_index: int,
        duration_overrides: dict[int, float] | None,
    ) -> float:
        phase = mission_plan.phases[active_phase_index]
        if phase.type is not PhaseType.TURN or phase.target_heading_deg is None:
            return 0.0

        start_heading = mission_plan.initial_state.heading_deg
        for previous in mission_plan.phases[:active_phase_index]:
            if previous.target_heading_deg is not None:
                start_heading = previous.target_heading_deg

        duration = self.interpolator.timeline.phase_duration(
            mission_plan,
            active_phase_index,
            duration_overrides,
        )
        if duration <= 0:
            return 0.0

        delta_deg = ((phase.target_heading_deg - start_heading + 540) % 360) - 180
        return radians(delta_deg / duration)

    def _battery_voltage(self, battery_percent: float) -> float:
        return 10.5 + self._clamp(battery_percent, 0.0, 100.0) / 100.0 * 2.1

    def _battery_current(self, ground_speed_m_s: float, vertical_speed_m_s: float) -> float:
        return 4.0 + ground_speed_m_s * 0.6 + max(vertical_speed_m_s, 0.0) * 1.4

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return min(max(value, minimum), maximum)
