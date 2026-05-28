import type {
  SnapshotUdpStreamStatusResponse,
  StreamPreviewResponse,
  UdpStreamStatusResponse,
} from "../../shared/api/types";

export type {
  SnapshotUdpStreamStatusResponse,
  StreamPreviewResponse,
  UdpStreamStatusResponse,
};

export type StreamPreviewKind = "synthetic" | "snapshot";

export type SelectedStreamPreview = {
  kind: StreamPreviewKind;
  streamId: string;
};
