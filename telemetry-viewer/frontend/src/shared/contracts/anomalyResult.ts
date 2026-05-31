export type Severity = "INFO" | "WARNING" | "CRITICAL";

export type EvidenceValue =
  | string
  | number
  | boolean
  | null
  | EvidenceValue[]
  | { [key: string]: EvidenceValue };

export type AnomalySource = {
  detector: string;
  confidence: number;
  evidence: Record<string, EvidenceValue>;
  severity?: Severity | null;
  message?: string | null;
};

export type AggregatedAnomaly = {
  type: string;
  severity: Severity;
  message: string;
  confidence: number;
  source: string;
  sources: AnomalySource[];
  detector_kind: string;
  detector_name: string;
  model_name?: string | null;
  score?: number | null;
  affected_fields: string[];
  affected_parameters: string[];
  evidence: Record<string, EvidenceValue>;
  window_start?: string | null;
  window_end?: string | null;
  probable_cause?: string | null;
  cause_confidence?: number | null;
  diagnostic_evidence: Record<string, EvidenceValue>;
  recommended_action?: string | null;
};

export type DetectedAnomaly = {
  type: string;
  severity: Severity;
  message: string;
  confidence: number;
  source: string;
  detector_kind: string;
  detector_name: string;
  model_name?: string | null;
  score?: number | null;
  affected_fields: string[];
  affected_parameters: string[];
  evidence: Record<string, EvidenceValue>;
  window_start?: string | null;
  window_end?: string | null;
  probable_cause?: string | null;
  cause_confidence?: number | null;
  diagnostic_evidence: Record<string, EvidenceValue>;
  recommended_action?: string | null;
};

export type DetectorOutput = {
  detector_name: string;
  detector_kind: string;
  status: "ready" | "not_ready" | string;
  message?: string | null;
  anomalies: DetectedAnomaly[];
};

export type AnomalyResult = {
  drone_id: string;
  telemetry_timestamp: string;
  has_anomalies: boolean;
  anomalies: AggregatedAnomaly[];
  detector_outputs: Record<string, DetectorOutput>;
};
