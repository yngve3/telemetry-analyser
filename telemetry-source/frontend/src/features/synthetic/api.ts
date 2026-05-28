import { apiRequest } from "../../shared/api/client";
import type {
  MissionCommandRequest,
  MissionCreatedResponse,
  MissionListItemResponse,
  MissionScriptRequest,
  MissionStatusResponse,
  TelemetrySampleResponse,
  UdpStreamRequest,
  UdpStreamStatusResponse,
} from "../../shared/api/types";

export function createSyntheticMission(
  payload: MissionScriptRequest,
): Promise<MissionCreatedResponse> {
  return apiRequest<MissionCreatedResponse>("/sources/synthetic/missions", {
    method: "POST",
    body: payload,
  });
}

export function listSyntheticMissions(): Promise<MissionListItemResponse[]> {
  return apiRequest<MissionListItemResponse[]>("/sources/synthetic/missions");
}

export function getSyntheticMissionStatus(
  missionId: string,
): Promise<MissionStatusResponse> {
  return apiRequest<MissionStatusResponse>(
    `/sources/synthetic/missions/${missionId}`,
  );
}

export function startSyntheticMission(
  missionId: string,
): Promise<MissionStatusResponse> {
  return runSyntheticMissionAction(missionId, "start");
}

export function pauseSyntheticMission(
  missionId: string,
): Promise<MissionStatusResponse> {
  return runSyntheticMissionAction(missionId, "pause");
}

export function resumeSyntheticMission(
  missionId: string,
): Promise<MissionStatusResponse> {
  return runSyntheticMissionAction(missionId, "resume");
}

export function stopSyntheticMission(
  missionId: string,
): Promise<MissionStatusResponse> {
  return runSyntheticMissionAction(missionId, "stop");
}

export function submitSyntheticMissionCommand(
  missionId: string,
  payload: MissionCommandRequest,
): Promise<MissionStatusResponse> {
  return apiRequest<MissionStatusResponse>(
    `/sources/synthetic/missions/${missionId}/commands`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export function getSyntheticSample(
  missionId: string,
): Promise<TelemetrySampleResponse> {
  return apiRequest<TelemetrySampleResponse>(
    `/sources/synthetic/missions/${missionId}/sample`,
  );
}

export function getSyntheticSampleBatch(
  missionId: string,
  count: number,
  deltaSec?: number,
): Promise<TelemetrySampleResponse[]> {
  return apiRequest<TelemetrySampleResponse[]>(
    `/sources/synthetic/missions/${missionId}/samples`,
    {
      query: {
        count,
        delta_sec: deltaSec,
      },
    },
  );
}

export function startSyntheticUdpStream(
  missionId: string,
  payload: UdpStreamRequest,
): Promise<UdpStreamStatusResponse> {
  return apiRequest<UdpStreamStatusResponse>(
    `/streams/synthetic/missions/${missionId}/udp`,
    {
      method: "POST",
      body: payload,
    },
  );
}

function runSyntheticMissionAction(
  missionId: string,
  action: "start" | "pause" | "resume" | "stop",
): Promise<MissionStatusResponse> {
  return apiRequest<MissionStatusResponse>(
    `/sources/synthetic/missions/${missionId}/${action}`,
    {
      method: "POST",
    },
  );
}
