import type {
  HealthResponse,
  SourceUdpStreamStatus,
} from "../contracts/analysisProfile";
import { TELEMETRY_SOURCE_API_BASE_URL } from "../config/env";
import { requestFromBase } from "./http";

export function getTelemetrySourceHealth(): Promise<HealthResponse> {
  return requestFromBase<HealthResponse>(TELEMETRY_SOURCE_API_BASE_URL, "/health");
}

export function listSyntheticUdpStreams(): Promise<SourceUdpStreamStatus[]> {
  return requestFromBase<SourceUdpStreamStatus[]>(
    TELEMETRY_SOURCE_API_BASE_URL,
    "/streams/udp",
  );
}

export function listSnapshotUdpStreams(): Promise<SourceUdpStreamStatus[]> {
  return requestFromBase<SourceUdpStreamStatus[]>(
    TELEMETRY_SOURCE_API_BASE_URL,
    "/streams/snapshots/udp",
  );
}
