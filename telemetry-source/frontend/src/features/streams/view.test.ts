import { describe, expect, it } from "vitest";

import { filterSyntheticStreams } from "./view";
import type { UdpStreamStatusResponse } from "../../shared/api/types";

const streams: UdpStreamStatusResponse[] = [
  {
    stream_id: "active",
    mission_id: "mission-a",
    host: "127.0.0.1",
    port: 14551,
    frequency_hz: 20,
    is_active: true,
    sent_count: 10,
  },
  {
    stream_id: "inactive",
    mission_id: "mission-b",
    host: "127.0.0.1",
    port: 14552,
    frequency_hz: 10,
    is_active: false,
    sent_count: 0,
  },
];

describe("filterSyntheticStreams", () => {
  it("keeps all streams by default", () => {
    expect(filterSyntheticStreams(streams, "all")).toHaveLength(2);
  });

  it("keeps only active streams", () => {
    expect(filterSyntheticStreams(streams, "active")).toEqual([streams[0]]);
  });
});
