import { apiRequest } from "../../shared/api/client";
import type {
  ExternalSourceCreateRequest,
  ExternalSourceCreatedResponse,
  ExternalSourceListItemResponse,
  ExternalSourceStatusResponse,
} from "../../shared/api/types";

export function createExternalSource(
  payload: ExternalSourceCreateRequest,
): Promise<ExternalSourceCreatedResponse> {
  return apiRequest<ExternalSourceCreatedResponse>("/sources/external", {
    method: "POST",
    body: payload,
  });
}

export function listExternalSources(): Promise<ExternalSourceListItemResponse[]> {
  return apiRequest<ExternalSourceListItemResponse[]>("/sources/external");
}

export function getExternalSourceStatus(
  sourceId: string,
): Promise<ExternalSourceStatusResponse> {
  return apiRequest<ExternalSourceStatusResponse>(`/sources/external/${sourceId}`);
}

export function startExternalSource(
  sourceId: string,
): Promise<ExternalSourceStatusResponse> {
  return apiRequest<ExternalSourceStatusResponse>(
    `/sources/external/${sourceId}/start`,
    {
      method: "POST",
    },
  );
}

export function stopExternalSource(
  sourceId: string,
): Promise<ExternalSourceStatusResponse> {
  return apiRequest<ExternalSourceStatusResponse>(
    `/sources/external/${sourceId}/stop`,
    {
      method: "POST",
    },
  );
}

export function deleteExternalSource(
  sourceId: string,
): Promise<{ source_id: string; deleted: boolean }> {
  return apiRequest<{ source_id: string; deleted: boolean }>(
    `/sources/external/${sourceId}`,
    {
      method: "DELETE",
    },
  );
}
