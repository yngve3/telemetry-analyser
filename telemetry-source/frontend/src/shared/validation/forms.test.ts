import { describe, expect, it } from "vitest";

import { validatePort, validateUdpTarget } from "./forms";

describe("form validators", () => {
  it("validates UDP ports", () => {
    expect(validatePort(14550)).toBeNull();
    expect(validatePort(0)).toContain("Port");
    expect(validatePort(70000)).toContain("Port");
  });

  it("validates UDP targets", () => {
    expect(validateUdpTarget({ host: "127.0.0.1", port: 14550 })).toBeNull();
    expect(validateUdpTarget({ host: "", port: 14550 })).toContain("Host");
    expect(
      validateUdpTarget({ host: "127.0.0.1", port: 14550, frequency_hz: 0 }),
    ).toContain("Frequency");
  });
});
