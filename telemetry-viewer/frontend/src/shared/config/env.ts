const rawAnalysisApiBaseUrl =
  import.meta.env.VITE_ANALYSIS_API_BASE_URL ?? "/api/analysis-service";
const rawTelemetrySourceApiBaseUrl =
  import.meta.env.VITE_TELEMETRY_SOURCE_API_BASE_URL ?? "/api/telemetry-source";

export const ANALYSIS_API_BASE_URL = rawAnalysisApiBaseUrl.replace(/\/$/, "");
export const TELEMETRY_SOURCE_API_BASE_URL =
  rawTelemetrySourceApiBaseUrl.replace(/\/$/, "");
