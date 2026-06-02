import type { AnomalyResult } from "../contracts/anomalyResult";
import type {
  AnalysisProfile,
  AnalysisSession,
  AnalysisSessionCreateRequest,
  AnalysisSessionLastResultResponse,
  AnalysisSessionLastTelemetryResponse,
  AnalysisSessionStateResponse,
  DetectorListResponse,
  HealthResponse,
  ListenerCreateRequest,
  ListenerResponse,
} from "../contracts/analysisProfile";
import type { TelemetryPayload } from "../contracts/telemetry";
import { ANALYSIS_API_BASE_URL } from "../config/env";
import { requestFromBase } from "./http";

type AnalyzeRequest = {
  format: "unified.telemetry";
  telemetry: TelemetryPayload;
};

export function getAnalysisHealth(): Promise<HealthResponse> {
  return requestFromBase<HealthResponse>(ANALYSIS_API_BASE_URL, "/health");
}

export function listDetectors(): Promise<DetectorListResponse> {
  return requestFromBase<DetectorListResponse>(
    ANALYSIS_API_BASE_URL,
    "/analysis/detectors",
  );
}

export function getAnalysisProfile(): Promise<AnalysisProfile> {
  return requestFromBase<AnalysisProfile>(
    ANALYSIS_API_BASE_URL,
    "/analysis/profile",
  );
}

export function updateAnalysisProfile(
  profile: AnalysisProfile,
): Promise<AnalysisProfile> {
  return requestFromBase<AnalysisProfile>(
    ANALYSIS_API_BASE_URL,
    "/analysis/profile",
    {
      method: "PUT",
      body: profile,
    },
  );
}

export function createAnalysisSession(
  payload: AnalysisSessionCreateRequest,
): Promise<AnalysisSession> {
  return requestFromBase<AnalysisSession>(
    ANALYSIS_API_BASE_URL,
    "/analysis/sessions",
    {
      method: "POST",
      body: payload,
    },
  );
}

export function getAnalysisSession(sessionId: string): Promise<AnalysisSession> {
  return requestFromBase<AnalysisSession>(
    ANALYSIS_API_BASE_URL,
    `/analysis/sessions/${sessionId}`,
  );
}

export function updateAnalysisSessionProfile(
  sessionId: string,
  profile: AnalysisProfile,
): Promise<AnalysisSession> {
  return requestFromBase<AnalysisSession>(
    ANALYSIS_API_BASE_URL,
    `/analysis/sessions/${sessionId}/profile`,
    {
      method: "PUT",
      body: profile,
    },
  );
}

export function deleteAnalysisSession(
  sessionId: string,
): Promise<{ session_id: string; deleted: boolean }> {
  return requestFromBase<{ session_id: string; deleted: boolean }>(
    ANALYSIS_API_BASE_URL,
    `/analysis/sessions/${sessionId}`,
    {
      method: "DELETE",
    },
  );
}

export function getAnalysisSessionLastResult(
  sessionId: string,
): Promise<AnalysisSessionLastResultResponse> {
  return requestFromBase<AnalysisSessionLastResultResponse>(
    ANALYSIS_API_BASE_URL,
    `/analysis/sessions/${sessionId}/last-result`,
  );
}

export function getAnalysisSessionLastTelemetry(
  sessionId: string,
): Promise<AnalysisSessionLastTelemetryResponse> {
  return requestFromBase<AnalysisSessionLastTelemetryResponse>(
    ANALYSIS_API_BASE_URL,
    `/analysis/sessions/${sessionId}/last-telemetry`,
  );
}

export function getAnalysisSessionState(
  sessionId: string,
): Promise<AnalysisSessionStateResponse> {
  return requestFromBase<AnalysisSessionStateResponse>(
    ANALYSIS_API_BASE_URL,
    `/analysis/sessions/${sessionId}/state`,
  );
}

export function analyzeUnifiedTelemetry(
  sessionId: string,
  telemetry: TelemetryPayload,
): Promise<AnomalyResult> {
  const payload: AnalyzeRequest = {
    format: "unified.telemetry",
    telemetry,
  };
  return requestFromBase<AnomalyResult>(
    ANALYSIS_API_BASE_URL,
    `/analysis/sessions/${sessionId}/analyze`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export function createListener(
  payload: ListenerCreateRequest,
): Promise<ListenerResponse> {
  return requestFromBase<ListenerResponse>(
    ANALYSIS_API_BASE_URL,
    "/analysis/listeners",
    {
      method: "POST",
      body: payload,
    },
  );
}

export function listListeners(): Promise<ListenerResponse[]> {
  return requestFromBase<ListenerResponse[]>(
    ANALYSIS_API_BASE_URL,
    "/analysis/listeners",
  );
}

export function getListener(listenerId: string): Promise<ListenerResponse> {
  return requestFromBase<ListenerResponse>(
    ANALYSIS_API_BASE_URL,
    `/analysis/listeners/${listenerId}`,
  );
}

export function deleteListener(
  listenerId: string,
): Promise<{ listener_id: string; deleted: boolean }> {
  return requestFromBase<{ listener_id: string; deleted: boolean }>(
    ANALYSIS_API_BASE_URL,
    `/analysis/listeners/${listenerId}`,
    {
      method: "DELETE",
    },
  );
}
