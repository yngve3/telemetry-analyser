import { apiRequest } from "../../shared/api/client";
import type {
  SnapshotUdpStreamStatusResponse,
  StreamPreviewResponse,
  UdpStreamStatusResponse,
} from "./types";

export function listSyntheticUdpStreams(): Promise<UdpStreamStatusResponse[]> {
  return apiRequest<UdpStreamStatusResponse[]>("/streams/udp");
}

export function stopSyntheticUdpStream(
  streamId: string,
): Promise<UdpStreamStatusResponse> {
  return apiRequest<UdpStreamStatusResponse>(`/streams/udp/${streamId}`, {
    method: "DELETE",
  });
}

export function getSyntheticUdpStreamPreview(
  streamId: string,
): Promise<StreamPreviewResponse> {
  return apiRequest<StreamPreviewResponse>(`/streams/udp/${streamId}/preview`);
}

export function listSnapshotUdpStreams(): Promise<SnapshotUdpStreamStatusResponse[]> {
  return apiRequest<SnapshotUdpStreamStatusResponse[]>("/streams/snapshots/udp");
}

export function stopSnapshotUdpStream(
  streamId: string,
): Promise<SnapshotUdpStreamStatusResponse> {
  return apiRequest<SnapshotUdpStreamStatusResponse>(
    `/streams/snapshots/udp/${streamId}`,
    {
      method: "DELETE",
    },
  );
}

export function getSnapshotUdpStreamPreview(
  streamId: string,
): Promise<StreamPreviewResponse> {
  return apiRequest<StreamPreviewResponse>(
    `/streams/snapshots/udp/${streamId}/preview`,
  );
}
