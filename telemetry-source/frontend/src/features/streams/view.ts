import type {
  SnapshotUdpStreamStatusResponse,
  UdpStreamStatusResponse,
} from "../../shared/api/types";

export type StreamFilter = "all" | "active";

export function filterSyntheticStreams(
  streams: UdpStreamStatusResponse[] | undefined,
  filter: StreamFilter,
): UdpStreamStatusResponse[] {
  return filterActive(streams ?? [], filter);
}

export function filterSnapshotStreams(
  streams: SnapshotUdpStreamStatusResponse[] | undefined,
  filter: StreamFilter,
): SnapshotUdpStreamStatusResponse[] {
  return filterActive(streams ?? [], filter);
}

function filterActive<T extends { is_active: boolean }>(
  streams: T[],
  filter: StreamFilter,
): T[] {
  if (filter === "active") {
    return streams.filter((stream) => stream.is_active);
  }
  return streams;
}
