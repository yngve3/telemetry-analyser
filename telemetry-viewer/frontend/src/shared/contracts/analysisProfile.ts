import type { AnomalyResult } from "./anomalyResult";
import type { TelemetryPayload } from "./telemetry";

export type HealthResponse = {
  status: string;
};

export type DetectorResponse = {
  name: string;
  kind: string;
  status: string;
  aliases: string[];
};

export type DetectorListResponse = {
  detectors: DetectorResponse[];
};

export type AnalysisProfile = {
  enabled_detectors: string[];
  enabled_rules: string[] | null;
  thresholds: Record<string, number>;
  history_size: number;
  model_window_size: number;
  model_artifact_path: string | null;
  ml_model_artifact_path: string | null;
  nn_model_artifact_path: string | null;
};

export type AnalysisSessionCreateRequest = {
  session_id?: string | null;
  drone_id?: string | null;
  profile?: AnalysisProfile | null;
};

export type AnalysisSession = {
  session_id: string;
  drone_id: string | null;
  created_at: string;
  last_analyzed_at: string | null;
  samples_analyzed: number;
  profile: AnalysisProfile;
};

export type AnalysisSessionLastResultResponse = {
  session_id: string;
  result: AnomalyResult | null;
};

export type AnalysisSessionLastTelemetryResponse = {
  session_id: string;
  telemetry: TelemetryPayload | null;
};

export type AnalysisSessionStateResponse = {
  session: AnalysisSession;
  last_telemetry: TelemetryPayload | null;
  last_result: AnomalyResult | null;
};

export type ListenerCreateRequest = {
  session_id: string;
  protocol: "udp";
  format: "mavlink.v2";
  bind_host: string;
  bind_port: number;
  buffer_size: number;
};

export type ListenerResponse = {
  listener_id: string;
  session_id: string;
  protocol: string;
  format: string;
  bind_host: string;
  bind_port: number;
  status: string;
  received_packets: number;
  received_bytes: number;
  converted_samples: number;
  analysis_errors: number;
  created_at: string;
  last_received_at: string | null;
  last_remote_address: string | null;
  last_remote_port: number | null;
  last_telemetry_timestamp: string | null;
  last_error: string | null;
  last_result: AnomalyResult | null;
};

export type SourceUdpStreamStatus = {
  stream_id: string;
  mission_id?: string;
  snapshot_id?: string;
  host: string;
  port: number;
  frequency_hz: number;
  is_active: boolean;
  sent_count?: number;
  samples_sent?: number;
  frames_sent?: number;
};
