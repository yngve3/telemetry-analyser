import { describe, expect, it } from "vitest";

import { defaultStep } from "./components/StepRow";
import { validateMissionScript } from "./validation";
import type { MissionScriptRequest } from "../../shared/api/types";

const validMission: MissionScriptRequest = {
  name: "simple_mission",
  frequency_hz: 20,
  drone_id: "uav-001",
  home: {
    latitude: 47.397742,
    longitude: 8.545594,
    altitude: 0,
    heading_deg: 0,
    battery: 100,
  },
  steps: [defaultStep("takeoff"), defaultStep("landing")],
  motion_profile: {
    horizontal_acceleration_m_s2: 2,
    default_climb_rate_m_s: 3,
    default_descent_rate_m_s: 2,
    default_yaw_rate_deg_s: 45,
    default_return_speed_m_s: 8,
  },
  noise_profile: {
    random_seed: null,
    gps_position_std_m: 0,
    altitude_std_m: 0,
    speed_std_m_s: 0,
    heading_std_deg: 0,
    battery_std_percent: 0,
  },
  battery_profile: {
    takeoff_percent_per_sec: 0.025,
    waypoint_percent_per_sec: 0.015,
    turn_percent_per_sec: 0.01,
    hover_percent_per_sec: 0.012,
    return_home_percent_per_sec: 0.015,
    landing_percent_per_sec: 0.01,
  },
};

describe("validateMissionScript", () => {
  it("accepts a valid mission", () => {
    expect(validateMissionScript(validMission)).toBeNull();
  });

  it("rejects invalid home latitude", () => {
    expect(
      validateMissionScript({
        ...validMission,
        home: { ...validMission.home, latitude: 120 },
      }),
    ).toContain("latitude");
  });

  it("rejects incomplete move_forward steps", () => {
    expect(
      validateMissionScript({
        ...validMission,
        steps: [{ type: "move_forward", distance_m: 10 }],
      }),
    ).toContain("speed_m_s");
  });
});
