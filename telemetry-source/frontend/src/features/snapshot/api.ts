import { apiRequest } from "../../shared/api/client";
import type {
  SnapshotCreatedResponse,
  SnapshotCreateRequest,
  SnapshotListItemResponse,
  SnapshotSamplesResponse,
  SnapshotSendOnceResponse,
  SnapshotStatusResponse,
  SnapshotUdpStreamStatusResponse,
  UdpStreamRequest,
} from "../../shared/api/types";

export function createSnapshot(
  payload: SnapshotCreateRequest,
): Promise<SnapshotCreatedResponse> {
  return apiRequest<SnapshotCreatedResponse>("/sources/snapshots", {
    method: "POST",
    body: payload,
  });
}

export function listSnapshots(): Promise<SnapshotListItemResponse[]> {
  return apiRequest<SnapshotListItemResponse[]>("/sources/snapshots");
}

export function getSnapshotStatus(
  snapshotId: string,
): Promise<SnapshotStatusResponse> {
  return apiRequest<SnapshotStatusResponse>(`/sources/snapshots/${snapshotId}`);
}

export function getSnapshotSamples(
  snapshotId: string,
): Promise<SnapshotSamplesResponse> {
  return apiRequest<SnapshotSamplesResponse>(
    `/sources/snapshots/${snapshotId}/samples`,
  );
}

export function sendSnapshotOnceUdp(
  snapshotId: string,
  payload: UdpStreamRequest,
): Promise<SnapshotSendOnceResponse> {
  return apiRequest<SnapshotSendOnceResponse>(
    `/sources/snapshots/${snapshotId}/send-once/udp`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export function startSnapshotUdpStream(
  snapshotId: string,
  payload: UdpStreamRequest,
): Promise<SnapshotUdpStreamStatusResponse> {
  return apiRequest<SnapshotUdpStreamStatusResponse>(
    `/streams/snapshots/${snapshotId}/udp`,
    {
      method: "POST",
      body: payload,
    },
  );
}
