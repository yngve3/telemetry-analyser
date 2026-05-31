export type Severity = "INFO" | "WARNING" | "CRITICAL";

export type AnomalySource = {
  detector: string;
  confidence: number;
  evidence: Record<string, string | number | boolean | null>;
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
  detector_name: string;
  affected_fields: string[];
  evidence: Record<string, string | number | boolean | null>;
};

export type DetectedAnomaly = {
  type: string;
  severity: Severity;
  message: string;
  confidence: number;
  source: string;
  detector_name: string;
  affected_fields: string[];
  evidence: Record<string, string | number | boolean | null>;
};

export type DetectorOutput = {
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
