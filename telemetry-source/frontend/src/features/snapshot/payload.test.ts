import { describe, expect, it } from "vitest";

import { buildSnapshotPayload } from "./payload";
import type { SnapshotSampleRequest } from "../../shared/api/types";

const sample: SnapshotSampleRequest = {
  timestamp: "2026-05-20T12:00:00+00:00",
  drone_id: "uav-001",
  latitude_deg: 47.397742,
  longitude_deg: 8.545594,
  altitude_m: 30,
  battery_percent: 90,
  satellites: 10,
};

describe("buildSnapshotPayload", () => {
  it("accepts a raw sample array", () => {
    const payload = buildSnapshotPayload(
      JSON.stringify([sample]),
      "snapshot",
      0.5,
      true,
    );

    expect(payload.name).toBe("snapshot");
    expect(payload.interval_seconds).toBe(0.5);
    expect(payload.repeat).toBe(true);
    expect(payload.samples).toHaveLength(1);
  });

  it("rejects an object without samples", () => {
    expect(() =>
      buildSnapshotPayload(JSON.stringify({ name: "snapshot" }), "snapshot", 1, false),
    ).toThrow("samples array");
  });

  it("rejects samples with missing required values", () => {
    expect(() =>
      buildSnapshotPayload(
        JSON.stringify({ samples: [{ ...sample, drone_id: "" }] }),
        "snapshot",
        1,
        false,
      ),
    ).toThrow("drone_id");
  });
});
