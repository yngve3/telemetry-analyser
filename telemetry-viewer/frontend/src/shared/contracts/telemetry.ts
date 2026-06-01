export type TelemetryPayload = {
  timestamp: string;
  drone_id: string;
  latitude_deg: number;
  longitude_deg: number;
  altitude_m: number;
  battery_percent: number;
  satellites: number;
  ground_speed_m_s?: number | null;
  vertical_speed_m_s?: number | null;
  heading_deg?: number | null;
  relative_altitude_m?: number | null;
  velocity_x_m_s?: number | null;
  velocity_y_m_s?: number | null;
  velocity_z_m_s?: number | null;
  roll_rad?: number | null;
  pitch_rad?: number | null;
  yaw_rad?: number | null;
  roll_rate_rad_s?: number | null;
  pitch_rate_rad_s?: number | null;
  yaw_rate_rad_s?: number | null;
  satellites_visible?: number | null;
  gps_fix_type?: number | null;
  gps_eph?: number | null;
  gps_epv?: number | null;
  battery_voltage_v?: number | null;
  battery_current_a?: number | null;
  system_status?: string | null;
  flight_mode?: string | null;
  armed?: boolean | null;
  sensor_health_flags?: number | null;
  attitude_age_ms?: number | null;
  position_age_ms?: number | null;
  gps_age_ms?: number | null;
  system_age_ms?: number | null;
  message_quality?: number | null;
  pos_test_ratio?: number | null;
  vel_test_ratio?: number | null;
  hgt_test_ratio?: number | null;
  mag_test_ratio?: number | null;
  hdg_test_ratio?: number | null;
  filter_fault_flags?: number | null;
  innovation_check_flags?: number | null;
  gps_check_fail_flags?: number | null;
  attitude_invalid?: number | null;
  angular_velocity_invalid?: number | null;
  local_position_invalid?: number | null;
  global_position_invalid?: number | null;
  local_velocity_invalid?: number | null;
  battery_warning?: number | null;
  fd_motor_failure?: number | null;
  fd_critical_failure?: number | null;
  fd_roll?: number | null;
  fd_pitch?: number | null;
  fd_alt?: number | null;
  fd_motor?: number | null;
  fd_battery?: number | null;
  fd_imbalanced_prop?: number | null;
};

export const sampleTelemetryPayload: TelemetryPayload = {
  timestamp: "2026-05-24T12:00:00+00:00",
  drone_id: "uav-001",
  latitude_deg: 47.397742,
  longitude_deg: 8.545594,
  altitude_m: 30,
  battery_percent: 20,
  satellites: 10,
  ground_speed_m_s: 8,
  vertical_speed_m_s: 0,
  heading_deg: 90,
  relative_altitude_m: 30,
  roll_rad: 0,
  pitch_rad: 0,
  yaw_rad: 1.5708,
  satellites_visible: 10,
  gps_fix_type: 3,
  gps_eph: 100,
  gps_epv: 150,
  battery_voltage_v: 12.2,
  battery_current_a: 8,
  system_status: "active",
  flight_mode: "auto",
  armed: true,
  sensor_health_flags: 4294967295,
  attitude_age_ms: 20,
  position_age_ms: 100,
  gps_age_ms: 200,
  system_age_ms: 1000,
  message_quality: 0.98,
};

export function parseTelemetryPayload(text: string): TelemetryPayload {
  const value = JSON.parse(text) as unknown;
  if (!isRecord(value)) {
    throw new Error("Telemetry payload must be a JSON object.");
  }

  const required = [
    "timestamp",
    "drone_id",
    "latitude_deg",
    "longitude_deg",
    "altitude_m",
    "battery_percent",
    "satellites",
  ] as const;
  const missing = required.filter((key) => value[key] === undefined);
  if (missing.length > 0) {
    throw new Error(`Telemetry payload is missing: ${missing.join(", ")}.`);
  }

  return value as TelemetryPayload;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
