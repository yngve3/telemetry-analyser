import type { components } from "./openapi";

type Schemas = components["schemas"];

export type HealthResponse = {
  status: string;
};

export type ScriptStepType = Schemas["ScriptStepType"];
export type TurnDirection = Schemas["TurnDirection"];
export type CommandType = Schemas["CommandType"];

export type AnomalyType =
  | "GPS_SIGNAL_LOSS"
  | "GPS_SPOOFING"
  | "IMU_SPIKE"
  | "MOTION_INCONSISTENCY"
  | "BATTERY_DROP"
  | "LOW_BATTERY"
  | "TELEMETRY_FREEZE"
  | "TELEMETRY_GAP"
  | "IMPOSSIBLE_ALTITUDE"
  | "ANOMALOUS_BEHAVIOR";

export type ScriptHomeRequest = Schemas["ScriptHomeRequest"];
export type ScriptStepRequest = Schemas["ScriptStepRequest"];
export type MotionProfileRequest = Schemas["MotionProfileRequest"];
export type NoiseProfileRequest = Schemas["NoiseProfileRequest"];
export type BatteryProfileRequest = Schemas["BatteryProfileRequest"];

export type MissionScriptRequest = Omit<
  Schemas["MissionScriptRequest"],
  "motion_profile" | "noise_profile" | "battery_profile"
> & {
  motion_profile: MotionProfileRequest;
  noise_profile: NoiseProfileRequest;
  battery_profile: BatteryProfileRequest;
};

export type MissionCommandRequest = Omit<
  Schemas["MissionCommandRequest"],
  "type"
> & {
  type?: AnomalyType | null;
};

export type UdpStreamRequest = Schemas["UdpStreamRequest"];
export type TelemetrySampleResponse = Schemas["TelemetrySampleResponse"];
export type StreamPreviewResponse = Schemas["StreamPreviewResponse"];
export type MissionStatusResponse = Schemas["MissionStatusResponse"];
export type MissionCreatedResponse = Schemas["MissionCreatedResponse"];
export type MissionListItemResponse = Schemas["MissionListItemResponse"];
export type UdpStreamStatusResponse = Schemas["UdpStreamStatusResponse"];

export type SnapshotSampleRequest = Schemas["SnapshotSampleRequest"];
export type SnapshotCreateRequest = Schemas["SnapshotCreateRequest"];
export type SnapshotStatusResponse = Schemas["SnapshotStatusResponse"];
export type SnapshotCreatedResponse = Schemas["SnapshotCreatedResponse"];
export type SnapshotListItemResponse = Schemas["SnapshotListItemResponse"];
export type SnapshotSendOnceResponse = Schemas["SnapshotSendOnceResponse"];
export type SnapshotUdpStreamStatusResponse =
  Schemas["SnapshotUdpStreamStatusResponse"];
export type SnapshotSamplesResponse = Schemas["SnapshotSamplesResponse"];

export type ExternalProtocol = Schemas["ExternalTransportProtocol"];
export type ExternalSourceCreateRequest = Schemas["ExternalSourceCreateRequest"];
export type ExternalSourceStatusResponse = Schemas["ExternalSourceStatusResponse"];
export type ExternalSourceCreatedResponse =
  Schemas["ExternalSourceCreatedResponse"];
export type ExternalSourceListItemResponse =
  Schemas["ExternalSourceListItemResponse"];

export type LanguageResponse = Schemas["LanguageResponse"];
export type TranslationsResponse = Schemas["TranslationsResponse"];
