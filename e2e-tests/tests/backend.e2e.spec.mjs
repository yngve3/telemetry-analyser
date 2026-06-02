import { expect, test } from "@playwright/test";

import {
  adaptiveCorrelationProfile,
  analyzeTelemetry,
  anomalyTypes,
  cleanupPipeline,
  createAnalysisSession,
  createListener,
  createMission,
  deleteJson,
  env,
  findAnomaly,
  getJson,
  hybridWithoutAutoencoderProfile,
  injectAnomaly,
  listenerPort,
  postJson,
  ruleBasedProfile,
  sendUdpPacket,
  startPipeline,
  telemetryPayload,
  uniqueId,
  waitForLastResult,
  waitForListenerSamples,
  waitForValue,
} from "./support/api.mjs";

test.describe("Backend E2E", () => {
  test("health checks", async ({ request }) => {
    const analysisHealth = await getJson(request, `${env.analysisBaseUrl}/health`);
    const sourceHealth = await getJson(request, `${env.sourceBaseUrl}/health`);

    expect(analysisHealth.status).toBe("ok");
    expect(sourceHealth.status).toBe("ok");
  });

  test("create rule-based analysis session", async ({ request }) => {
    const sessionId = uniqueId("rule-based");

    try {
      await createAnalysisSession(request, {
        sessionId,
        profile: ruleBasedProfile(),
      });

      const session = await getJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );

      expect(session.session_id).toBe(sessionId);
      expect(session.samples_analyzed).toBe(0);
      expect(session.profile.enabled_detectors).toContain("rule_based");
    } finally {
      await request.delete(`${env.analysisBaseUrl}/analysis/sessions/${sessionId}`);
    }
  });

  test("manual normal telemetry", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("normal"),
      profile: ruleBasedProfile(),
    });

    try {
      const result = await analyzeTelemetry(request, sessionId, telemetryPayload());

      expect(result.anomalies).toEqual([]);
      expect(result.detector_outputs.rule_based.anomalies).toEqual([]);
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("manual low battery detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("low-battery"),
      profile: ruleBasedProfile(),
    });

    try {
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({ battery_percent: 10 }),
      );
      const anomaly = findAnomaly(result, "LOW_BATTERY");

      expect(anomaly).toBeTruthy();
      expect(anomaly.sources.map((source) => source.detector)).toContain(
        "rule_based",
      );
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("manual GPS signal loss detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("gps-signal-loss"),
      profile: ruleBasedProfile({ enabled_rules: ["gps_signal_loss"] }),
    });

    try {
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          satellites: 0,
          satellites_visible: 0,
          gps_fix_type: 0,
        }),
      );
      const anomaly = findAnomaly(result, "GPS_SIGNAL_LOSS");

      expect(anomaly).toBeTruthy();
      expect(anomaly.severity).toBe("CRITICAL");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("manual impossible altitude detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("impossible-altitude"),
      profile: ruleBasedProfile({ enabled_rules: ["impossible_altitude"] }),
    });

    try {
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({ altitude_m: -1000 }),
      );

      expect(anomalyTypes(result)).toContain("IMPOSSIBLE_ALTITUDE");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("stateful battery drop detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("battery-drop"),
      profile: ruleBasedProfile({ enabled_rules: ["battery_drop"] }),
    });

    try {
      const firstResult = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:00.000Z",
          battery_percent: 90,
        }),
      );
      const secondResult = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:02.000Z",
          battery_percent: 80,
        }),
      );
      const session = await getJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );

      expect(anomalyTypes(firstResult)).not.toContain("BATTERY_DROP");
      expect(anomalyTypes(secondResult)).toContain("BATTERY_DROP");
      expect(session.samples_analyzed).toBe(2);
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("stateful GPS spoofing detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("gps-spoofing"),
      profile: ruleBasedProfile({ enabled_rules: ["gps_spoofing"] }),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:00.000Z",
          latitude_deg: 47.397742,
          longitude_deg: 8.545594,
          ground_speed_m_s: 8,
        }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:01.000Z",
          latitude_deg: 47.399742,
          longitude_deg: 8.545594,
          ground_speed_m_s: 8,
        }),
      );
      const anomaly = findAnomaly(result, "GPS_SPOOFING");

      expect(anomaly).toBeTruthy();
      expect(anomaly.sources[0].evidence).toHaveProperty("distance_delta_m");
      expect(anomaly.sources[0].evidence).toHaveProperty(
        "calculated_speed_m_s",
      );
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("stateful IMU spike detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("imu-spike"),
      profile: ruleBasedProfile({ enabled_rules: ["imu_spike"] }),
    });

    try {
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({ roll_rate_rad_s: 8 }),
      );

      expect(anomalyTypes(result)).toContain("IMU_SPIKE");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("motion inconsistency detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("motion-inconsistency"),
      profile: ruleBasedProfile({ enabled_rules: ["motion_inconsistency"] }),
    });

    try {
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          ground_speed_m_s: 1,
          velocity_x_m_s: 20,
          velocity_y_m_s: 0,
        }),
      );

      expect(anomalyTypes(result)).toContain("MOTION_INCONSISTENCY");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("telemetry freeze detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("telemetry-freeze"),
      profile: ruleBasedProfile({ enabled_rules: ["telemetry_freeze"] }),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({ timestamp: "2026-05-24T12:00:06.000Z" }),
      );

      expect(anomalyTypes(result)).toContain("TELEMETRY_FREEZE");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("telemetry gap detection", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("telemetry-gap"),
      profile: ruleBasedProfile({ enabled_rules: ["telemetry_gap"] }),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({ timestamp: "2026-05-24T12:00:20.000Z" }),
      );

      expect(anomalyTypes(result)).toContain("TELEMETRY_GAP");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("disabled rule is not reported", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("disabled-rule"),
      profile: ruleBasedProfile({ enabled_rules: ["low_battery"] }),
    });

    try {
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          battery_percent: 10,
          altitude_m: 50_000,
        }),
      );
      const types = anomalyTypes(result);

      expect(types).toContain("LOW_BATTERY");
      expect(types).not.toContain("IMPOSSIBLE_ALTITUDE");
      expect(
        result.detector_outputs.rule_based.anomalies.map(
          (anomaly) => anomaly.type,
        ),
      ).not.toContain("IMPOSSIBLE_ALTITUDE");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("analysis sessions keep isolated state", async ({ request }) => {
    const firstSessionId = uniqueId("isolated-first");
    const secondSessionId = uniqueId("isolated-second");

    try {
      await createAnalysisSession(request, {
        sessionId: firstSessionId,
        profile: ruleBasedProfile({ enabled_rules: ["battery_drop"] }),
      });
      await createAnalysisSession(request, {
        sessionId: secondSessionId,
        profile: ruleBasedProfile({ enabled_rules: ["battery_drop"] }),
      });

      await analyzeTelemetry(
        request,
        firstSessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:00.000Z",
          battery_percent: 90,
        }),
      );
      const secondSessionResult = await analyzeTelemetry(
        request,
        secondSessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:02.000Z",
          battery_percent: 80,
        }),
      );
      const firstSessionResult = await analyzeTelemetry(
        request,
        firstSessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:02.000Z",
          battery_percent: 80,
        }),
      );

      const firstSession = await getJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${firstSessionId}`,
      );
      const secondSession = await getJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${secondSessionId}`,
      );

      expect(anomalyTypes(secondSessionResult)).not.toContain("BATTERY_DROP");
      expect(anomalyTypes(firstSessionResult)).toContain("BATTERY_DROP");
      expect(firstSession.samples_analyzed).toBe(2);
      expect(secondSession.samples_analyzed).toBe(1);
    } finally {
      await request.delete(
        `${env.analysisBaseUrl}/analysis/sessions/${firstSessionId}`,
      );
      await request.delete(
        `${env.analysisBaseUrl}/analysis/sessions/${secondSessionId}`,
      );
    }
  });

  test("create adaptive correlation analysis session", async ({ request }) => {
    const sessionId = uniqueId("adaptive-session");

    try {
      await createAnalysisSession(request, {
        sessionId,
        profile: adaptiveCorrelationProfile(),
      });

      const session = await getJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );

      expect(session.profile.enabled_detectors).toEqual([
        "rule_based",
        "adaptive_correlation_based",
      ]);
      expect(session.samples_analyzed).toBe(0);
    } finally {
      await request.delete(`${env.analysisBaseUrl}/analysis/sessions/${sessionId}`);
    }
  });

  test("manual normal telemetry with adaptive correlation profile", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-normal"),
      profile: adaptiveCorrelationProfile(),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          longitude_deg: 8.54562,
          ground_speed_m_s: 1.9,
          velocity_x_m_s: 0,
          velocity_y_m_s: 1.9,
        }),
      );

      expect(result.anomalies).toEqual([]);
      expect(result.detector_outputs).toHaveProperty(
        "adaptive_correlation_based",
      );
      expect(result.detector_outputs.adaptive_correlation_based.status).toBe(
        "ready",
      );
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("adaptive correlation detects position-speed inconsistency", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-position-speed"),
      profile: { enabled_detectors: ["adaptive_correlation_based"] },
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          latitude_deg: 47.399742,
          ground_speed_m_s: 1,
          velocity_x_m_s: 0,
          velocity_y_m_s: 1,
        }),
      );
      const anomaly = findAnomaly(result, "MOTION_INCONSISTENCY");
      const source = sourceForDetector(anomaly, "adaptive_correlation_based");

      expect(source).toBeTruthy();
      expect(source.evidence.errors.position_speed_error).toBeGreaterThan(8);
      expect(source.evidence.exceeded_errors).toHaveProperty(
        "position_speed_error",
      );
      expect(source.evidence.mode).toBe("calibration");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("adaptive correlation detects altitude-vertical-speed inconsistency", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-altitude"),
      profile: { enabled_detectors: ["adaptive_correlation_based"] },
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:00.000Z",
          altitude_m: 30,
          relative_altitude_m: 30,
        }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          altitude_m: 60,
          relative_altitude_m: 60,
          vertical_speed_m_s: 0,
          velocity_z_m_s: 0,
        }),
      );
      const anomaly = findAnomaly(result, "MOTION_INCONSISTENCY");
      const source = sourceForDetector(anomaly, "adaptive_correlation_based");

      expect(source).toBeTruthy();
      expect(source.evidence.exceeded_errors).toHaveProperty(
        "altitude_velocity_error",
      );
      expect(anomaly.affected_parameters).toEqual(
        expect.arrayContaining(["altitude_m", "vertical_speed_m_s"]),
      );
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("adaptive correlation detects heading-yaw inconsistency", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-heading-yaw"),
      profile: { enabled_detectors: ["adaptive_correlation_based"] },
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          longitude_deg: 8.546594,
          ground_speed_m_s: 75,
          velocity_x_m_s: 0,
          velocity_y_m_s: 75,
          yaw_rad: 3.14159,
        }),
      );
      const anomaly = findAnomaly(result, "MOTION_INCONSISTENCY");
      const source = sourceForDetector(anomaly, "adaptive_correlation_based");

      expect(source).toBeTruthy();
      expect(source.evidence.exceeded_errors).toHaveProperty("heading_yaw_error");
      expect(source.evidence).toHaveProperty("movement_heading_deg");
      expect(source.evidence).toHaveProperty("yaw_deg");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("adaptive correlation reports stale telemetry as not ready", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-stale"),
      profile: { enabled_detectors: ["adaptive_correlation_based"] },
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          latitude_deg: 47.399742,
          ground_speed_m_s: 1,
          message_quality: 0.1,
        }),
      );

      expect(result.anomalies).toEqual([]);
      expect(result.detector_outputs.adaptive_correlation_based.status).toBe(
        "not_ready",
      );
      expect(result.detector_outputs.adaptive_correlation_based.message).toContain(
        "Telemetry freshness",
      );
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("adaptive correlation profile updates on normal telemetry", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-profile-update"),
      profile: { enabled_detectors: ["adaptive_correlation_based"] },
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          longitude_deg: 8.54562,
          ground_speed_m_s: 1.9,
          velocity_y_m_s: 1.9,
        }),
      );
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:02.000Z",
          longitude_deg: 8.545646,
          ground_speed_m_s: 1.9,
          velocity_y_m_s: 1.9,
        }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:03.000Z",
          latitude_deg: 47.399742,
          longitude_deg: 8.545646,
          ground_speed_m_s: 1,
          velocity_y_m_s: 1,
        }),
      );
      const anomaly = findAnomaly(result, "MOTION_INCONSISTENCY");
      const source = sourceForDetector(anomaly, "adaptive_correlation_based");

      expect(source.evidence.profile_counts.position_speed_error).toBe(2);
      expect(source.evidence.profile_counts.altitude_velocity_error).toBe(2);
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("rule-based and adaptive correlation aggregate shared anomaly", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-aggregation"),
      profile: adaptiveCorrelationProfile({
        enabled_rules: ["motion_inconsistency"],
      }),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          latitude_deg: 47.399742,
          ground_speed_m_s: 1,
          velocity_x_m_s: 20,
          velocity_y_m_s: 0,
        }),
      );
      const motionAnomalies = result.anomalies.filter(
        (anomaly) => anomaly.type === "MOTION_INCONSISTENCY",
      );
      const anomaly = motionAnomalies[0];

      expect(motionAnomalies).toHaveLength(1);
      expect(anomaly.sources.map((source) => source.detector)).toEqual(
        expect.arrayContaining(["rule_based", "adaptive_correlation_based"]),
      );
      expect(result.detector_outputs.rule_based.anomalies).toHaveLength(1);
      expect(
        result.detector_outputs.adaptive_correlation_based.anomalies,
      ).toHaveLength(1);
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("adaptive correlation result includes timing", async ({ request }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-timing"),
      profile: adaptiveCorrelationProfile(),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          longitude_deg: 8.54562,
          ground_speed_m_s: 1.9,
          velocity_y_m_s: 1.9,
        }),
      );

      expect(result.timing.total_ms).toBeGreaterThanOrEqual(0);
      expect(result.timing.detectors.rule_based.duration_ms).toBeGreaterThanOrEqual(
        0,
      );
      expect(
        result.timing.detectors.adaptive_correlation_based.duration_ms,
      ).toBeGreaterThanOrEqual(0);
      expect(result.timing.detectors.rule_based.status).toBe("ready");
      expect(result.timing.detectors.adaptive_correlation_based.status).toBe(
        "ready",
      );
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("adaptive correlation timing is returned in last result", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("adaptive-last-result"),
      profile: adaptiveCorrelationProfile(),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({ timestamp: "2026-05-24T12:00:00.000Z" }),
      );
      await analyzeTelemetry(
        request,
        sessionId,
        adaptiveTelemetry({
          timestamp: "2026-05-24T12:00:01.000Z",
          longitude_deg: 8.54562,
          ground_speed_m_s: 1.9,
          velocity_y_m_s: 1.9,
        }),
      );
      const lastResult = await getJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}/last-result`,
      );

      expect(lastResult.result.timing.total_ms).toBeGreaterThanOrEqual(0);
      expect(lastResult.result.timing.detectors).toHaveProperty(
        "adaptive_correlation_based",
      );
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("hybrid analysis without autoencoder exposes expected detectors", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("hybrid-no-autoencoder"),
      profile: hybridWithoutAutoencoderProfile(),
    });

    try {
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload(),
      );

      expect(Object.keys(result.detector_outputs)).toEqual([
        "rule_based",
        "correlation_based",
        "isolation_forest",
      ]);
      expect(result.detector_outputs).not.toHaveProperty("autoencoder");
      expect(result.detector_outputs.isolation_forest.status).toBe("ready");
      expect(result.status).toBe("NORMAL");
      expect(result.risk_level).toBe("NONE");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("hybrid analysis without autoencoder accepts PX4 diagnostic fields", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("hybrid-px4-fields"),
      profile: hybridWithoutAutoencoderProfile(),
    });

    try {
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          pos_test_ratio: 0.1,
          vel_test_ratio: 0.1,
          hgt_test_ratio: 0.1,
          mag_test_ratio: 0.1,
          hdg_test_ratio: 0.1,
          filter_fault_flags: 0,
          innovation_check_flags: 0,
          gps_check_fail_flags: 0,
          attitude_invalid: 0,
          angular_velocity_invalid: 0,
          local_position_invalid: 0,
          global_position_invalid: 0,
          local_velocity_invalid: 0,
          battery_warning: 0,
          fd_motor_failure: 0,
          fd_critical_failure: 0,
          fd_roll: 0,
          fd_pitch: 0,
          fd_alt: 0,
          fd_motor: 0,
          fd_battery: 0,
          fd_imbalanced_prop: 0,
        }),
      );

      expect(result.detector_outputs).toHaveProperty("isolation_forest");
      expect(result.detector_outputs).not.toHaveProperty("autoencoder");
      expect(result.anomalies).toEqual([]);
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("hybrid analysis without autoencoder detects motion anomaly", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("hybrid-motion"),
      profile: hybridWithoutAutoencoderProfile({
        enabled_rules: ["motion_inconsistency"],
      }),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:00.000Z",
          ground_speed_m_s: 1,
          velocity_x_m_s: 1,
          velocity_y_m_s: 0,
        }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:01.000Z",
          latitude_deg: 47.399742,
          ground_speed_m_s: 1,
          velocity_x_m_s: 20,
          velocity_y_m_s: 0,
        }),
      );
      const anomaly = findAnomaly(result, "MOTION_INCONSISTENCY");

      expect(anomaly).toBeTruthy();
      expect(anomaly.sources.map((source) => source.detector)).toEqual(
        expect.arrayContaining(["rule_based", "correlation_based"]),
      );
      expect(result.detector_outputs).toHaveProperty("isolation_forest");
      expect(result.detector_outputs).not.toHaveProperty("autoencoder");
      expect(result.has_anomalies).toBe(true);
      expect(result.risk_level).toMatch(/MEDIUM|HIGH/);
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("hybrid analysis ranks primary anomaly before additional anomalies", async ({
    request,
  }) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("hybrid-primary"),
      profile: hybridWithoutAutoencoderProfile({
        enabled_rules: ["low_battery", "motion_inconsistency"],
      }),
    });

    try {
      await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:00.000Z",
          battery_percent: 18,
          ground_speed_m_s: 1,
          velocity_x_m_s: 1,
          velocity_y_m_s: 0,
        }),
      );
      const result = await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({
          timestamp: "2026-05-24T12:00:01.000Z",
          battery_percent: 18,
          latitude_deg: 47.399742,
          ground_speed_m_s: 1,
          velocity_x_m_s: 20,
          velocity_y_m_s: 0,
        }),
      );

      expect(result.anomalies.length).toBeGreaterThanOrEqual(2);
      expect(result.anomalies[0].type).toBe("MOTION_INCONSISTENCY");
      expect(result.anomalies[0].severity).toBe("CRITICAL");
      expect(result.anomalies.map((anomaly) => anomaly.type)).toContain(
        "LOW_BATTERY",
      );
      expect(result.anomalies[0].sources.map((source) => source.detector)).toEqual(
        expect.arrayContaining(["rule_based", "correlation_based"]),
      );
      expect(result.detector_outputs).toHaveProperty("rule_based");
      expect(result.detector_outputs).toHaveProperty("correlation_based");
      expect(result.detector_outputs).toHaveProperty("isolation_forest");
      expect(result.detector_outputs).not.toHaveProperty("autoencoder");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("external source receives UDP packets on compose default port", async ({
    request,
  }) => {
    const createdSource = await postJson(
      request,
      `${env.sourceBaseUrl}/sources/external`,
      {
        name: uniqueId("external-mavlink"),
      },
      201,
    );
    const sourceId = createdSource.source_id;
    const status = createdSource.status;

    expect(status.address).toBe("0.0.0.0");
    expect(status.port).toBe(14540);

    try {
      const started = await postJson(
        request,
        `${env.sourceBaseUrl}/sources/external/${sourceId}/start`,
        {},
      );
      expect(started.is_active).toBe(true);

      await sendUdpPacket(
        new URL(env.sourceBaseUrl).hostname,
        14540,
        "mavlink-frame",
      );
      const received = await waitForValue(
        async () =>
          getJson(request, `${env.sourceBaseUrl}/sources/external/${sourceId}`),
        (payload) => payload.received_packets >= 1,
        "external source to receive UDP packet",
      );

      expect(received.received_bytes).toBeGreaterThan(0);
      expect(received.last_payload_size).toBe("mavlink-frame".length);
      expect(received.last_error).toBeFalsy();
    } finally {
      await postJson(
        request,
        `${env.sourceBaseUrl}/sources/external/${sourceId}/stop`,
        {},
      );
    }
  });

  test("external source forwards MAVLink stream into analysis listener", async (
    { request },
    testInfo,
  ) => {
    const sessionId = uniqueId("external-forward");
    const analysisPort = listenerPort(testInfo);
    const externalPort = listenerPort(testInfo) + 500;
    let listenerId = null;
    let sourceId = null;
    let streamId = null;

    try {
      await createAnalysisSession(request, {
        sessionId,
        profile: ruleBasedProfile(),
      });
      const listener = await createListener(request, sessionId, analysisPort);
      listenerId = listener.listener_id;
      await waitForValue(
        async () =>
          getJson(request, `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`),
        (payload) => payload.status === "active",
        "external forward listener to become active",
      );

      const createdSource = await postJson(
        request,
        `${env.sourceBaseUrl}/sources/external`,
        {
          name: uniqueId("external-forward"),
          address: "0.0.0.0",
          port: externalPort,
          protocol: "udp",
          forward_enabled: true,
          forward_host: env.streamTargetHost,
          forward_port: analysisPort,
        },
        201,
      );
      sourceId = createdSource.source_id;
      await postJson(
        request,
        `${env.sourceBaseUrl}/sources/external/${sourceId}/start`,
        {},
      );

      const mission = await createMission(request, uniqueId("external-mission"));
      const stream = await postJson(
        request,
        `${env.sourceBaseUrl}/streams/synthetic/missions/${mission.mission_id}/udp`,
        {
          host: "127.0.0.1",
          port: externalPort,
          frequency_hz: 20,
        },
        201,
      );
      streamId = stream.stream_id;

      const source = await waitForValue(
        async () =>
          getJson(request, `${env.sourceBaseUrl}/sources/external/${sourceId}`),
        (payload) =>
          payload.received_packets > 0 &&
          payload.forwarded_packets > 0 &&
          Boolean(payload.last_payload_preview_hex),
        "external source forwarded stream",
      );
      const listenerStatus = await waitForListenerSamples(request, listenerId);
      const result = await waitForLastResult(
        request,
        sessionId,
        (payload) => Boolean(payload.detector_outputs?.rule_based),
      );

      expect(source.received_packets).toBeGreaterThan(0);
      expect(source.forwarded_packets).toBeGreaterThan(0);
      expect(source.last_forward_error).toBeFalsy();
      expect(listenerStatus.received_packets).toBeGreaterThan(0);
      expect(listenerStatus.converted_samples).toBeGreaterThan(0);
      expect(result.detector_outputs).toHaveProperty("rule_based");
    } finally {
      if (streamId) {
        await deleteJson(request, `${env.sourceBaseUrl}/streams/udp/${streamId}`);
      }
      if (sourceId) {
        await postJson(
          request,
          `${env.sourceBaseUrl}/sources/external/${sourceId}/stop`,
          {},
        );
      }
      if (listenerId) {
        await deleteJson(
          request,
          `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
        );
      }
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("create UDP MAVLink listener", async ({ request }, testInfo) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("listener"),
      profile: ruleBasedProfile(),
    });

    let listenerId = null;
    try {
      const createdListener = await createListener(
        request,
        sessionId,
        listenerPort(testInfo),
      );
      listenerId = createdListener.listener_id;
      const listener = await waitForValue(
        async () =>
          getJson(
            request,
            `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
          ),
        (payload) => payload.status === "active",
        "listener to become active",
      );

      expect(listener.status).toBe("active");
      expect(listener.received_packets).toBe(0);
      expect(listener.converted_samples).toBe(0);
    } finally {
      if (listenerId) {
        await deleteJson(
          request,
          `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
        );
      }
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("invalid UDP packet does not break listener", async (
    { request },
    testInfo,
  ) => {
    const { sessionId } = await createAnalysisSession(request, {
      sessionId: uniqueId("invalid-udp"),
      profile: ruleBasedProfile(),
    });
    const port = listenerPort(testInfo);
    let listenerId = null;

    try {
      const createdListener = await createListener(request, sessionId, port);
      listenerId = createdListener.listener_id;

      await waitForValue(
        async () =>
          getJson(
            request,
            `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
          ),
        (payload) => payload.status === "active",
        "invalid packet listener to become active",
      );
      await sendUdpPacket(env.streamTargetHost, port, "not-a-mavlink-frame");

      const listener = await waitForValue(
        async () =>
          getJson(
            request,
            `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
          ),
        (payload) => payload.received_packets > 0 && payload.analysis_errors > 0,
        "listener analysis error",
      );

      expect(listener.status).toBe("active");
      expect(listener.converted_samples).toBe(0);
      expect(listener.last_error).toBeTruthy();
    } finally {
      if (listenerId) {
        await deleteJson(
          request,
          `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
        );
      }
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("deleting session cleans attached listener", async (
    { request },
    testInfo,
  ) => {
    const sessionId = uniqueId("cleanup-session");
    const port = listenerPort(testInfo);
    let listenerId = null;

    try {
      await createAnalysisSession(request, {
        sessionId,
        profile: ruleBasedProfile(),
      });
      const createdListener = await createListener(request, sessionId, port);
      listenerId = createdListener.listener_id;
      await waitForValue(
        async () =>
          getJson(
            request,
            `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
          ),
        (payload) => payload.status === "active",
        "cleanup listener to become active",
      );

      const deletedSession = await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
      const listenerAfterDelete = await request.get(
        `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
      );

      listenerId = null;

      expect(deletedSession.deleted).toBe(true);
      expect(listenerAfterDelete.status()).toBe(404);
    } finally {
      if (listenerId) {
        await request.delete(
          `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`,
        );
      }
      await request.delete(`${env.analysisBaseUrl}/analysis/sessions/${sessionId}`);
    }
  });

  test("listener port conflict is rejected", async ({ request }, testInfo) => {
    const firstSessionId = uniqueId("port-conflict-first");
    const secondSessionId = uniqueId("port-conflict-second");
    const port = listenerPort(testInfo);
    let firstListenerId = null;

    try {
      await createAnalysisSession(request, {
        sessionId: firstSessionId,
        profile: ruleBasedProfile(),
      });
      await createAnalysisSession(request, {
        sessionId: secondSessionId,
        profile: ruleBasedProfile(),
      });

      const firstListener = await createListener(request, firstSessionId, port);
      firstListenerId = firstListener.listener_id;
      const conflictResponse = await request.post(
        `${env.analysisBaseUrl}/analysis/listeners`,
        {
          data: {
            session_id: secondSessionId,
            protocol: "udp",
            format: "mavlink.v2",
            bind_host: env.listenerBindHost,
            bind_port: port,
            buffer_size: 4096,
          },
        },
      );
      const conflictPayload = await conflictResponse.json();

      expect(conflictResponse.status()).toBe(422);
      expect(conflictPayload.detail).toContain("already exists");
    } finally {
      if (firstListenerId) {
        await request.delete(
          `${env.analysisBaseUrl}/analysis/listeners/${firstListenerId}`,
        );
      }
      await request.delete(
        `${env.analysisBaseUrl}/analysis/sessions/${firstSessionId}`,
      );
      await request.delete(
        `${env.analysisBaseUrl}/analysis/sessions/${secondSessionId}`,
      );
    }
  });

  test("generator stream normal flight with adaptive correlation", async (
    { request },
    testInfo,
  ) => {
    const pipeline = await startPipeline(request, testInfo, {
      profile: adaptiveCorrelationProfile(),
    });

    try {
      const listener = await waitForListenerSamples(
        request,
        pipeline.listenerId,
      );
      const result = await waitForLastResult(
        request,
        pipeline.sessionId,
        (payload) =>
          Boolean(payload.detector_outputs?.rule_based) &&
          Boolean(payload.detector_outputs?.adaptive_correlation_based),
      );

      expect(listener.received_packets).toBeGreaterThan(0);
      expect(listener.converted_samples).toBeGreaterThan(0);
      expect(result.detector_outputs.adaptive_correlation_based.status).toMatch(
        /ready|not_ready/,
      );
      expect(result.timing.detectors).toHaveProperty(
        "adaptive_correlation_based",
      );
      expect(
        result.anomalies.filter((anomaly) => anomaly.severity === "CRITICAL"),
      ).toEqual([]);
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("generator stream to analysis listener: normal flight", async (
    { request },
    testInfo,
  ) => {
    const pipeline = await startPipeline(request, testInfo);

    try {
      const listener = await waitForListenerSamples(
        request,
        pipeline.listenerId,
      );
      const result = await waitForLastResult(
        request,
        pipeline.sessionId,
        (payload) => Boolean(payload.detector_outputs?.rule_based),
      );

      expect(listener.received_packets).toBeGreaterThan(0);
      expect(listener.converted_samples).toBeGreaterThan(0);
      expect(result.detector_outputs).toHaveProperty("rule_based");
      expect(
        result.anomalies.filter((anomaly) => anomaly.severity === "CRITICAL"),
      ).toEqual([]);
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("generator stream GPS signal loss injection", async (
    { request },
    testInfo,
  ) => {
    const pipeline = await startPipeline(request, testInfo);

    try {
      await waitForListenerSamples(request, pipeline.listenerId);
      await injectAnomaly(request, pipeline.missionId, "GPS_SIGNAL_LOSS");

      const result = await waitForLastResult(request, pipeline.sessionId, (payload) =>
        anomalyTypes(payload).includes("GPS_SIGNAL_LOSS"),
      );
      const anomaly = findAnomaly(result, "GPS_SIGNAL_LOSS");

      expect(anomaly.sources.map((source) => source.detector)).toContain(
        "rule_based",
      );
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("generator stream GPS spoofing injection", async (
    { request },
    testInfo,
  ) => {
    const pipeline = await startPipeline(request, testInfo, {
      profile: ruleBasedProfile({
        thresholds: {
          "gps_spoofing.max_implied_speed_m_s": 10,
          "gps_spoofing.speed_margin_m_s": 0,
          "gps_spoofing.min_distance_delta_m": 5,
        },
      }),
    });

    try {
      await waitForListenerSamples(request, pipeline.listenerId);
      await injectAnomaly(request, pipeline.missionId, "GPS_SPOOFING");

      const result = await waitForLastResult(
        request,
        pipeline.sessionId,
        (payload) => anomalyTypes(payload).includes("GPS_SPOOFING"),
        { intervalMs: 10 },
      );

      expect(anomalyTypes(result)).toContain("GPS_SPOOFING");
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("generator stream IMU spike injection", async ({ request }, testInfo) => {
    const pipeline = await startPipeline(request, testInfo);

    try {
      await waitForListenerSamples(request, pipeline.listenerId);
      await injectAnomaly(request, pipeline.missionId, "IMU_SPIKE");

      const result = await waitForLastResult(request, pipeline.sessionId, (payload) =>
        anomalyTypes(payload).includes("IMU_SPIKE"),
      );

      expect(anomalyTypes(result)).toContain("IMU_SPIKE");
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("generator stream battery drop injection", async (
    { request },
    testInfo,
  ) => {
    const pipeline = await startPipeline(request, testInfo);

    try {
      await waitForListenerSamples(request, pipeline.listenerId);
      await injectAnomaly(request, pipeline.missionId, "BATTERY_DROP");

      const result = await waitForLastResult(request, pipeline.sessionId, (payload) => {
        const types = anomalyTypes(payload);
        return types.includes("BATTERY_DROP") || types.includes("LOW_BATTERY");
      });
      const types = anomalyTypes(result);

      expect(
        types.includes("BATTERY_DROP") || types.includes("LOW_BATTERY"),
      ).toBe(true);
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("stop stream and listener", async ({ request }, testInfo) => {
    const pipeline = await startPipeline(request, testInfo);

    try {
      const stoppedStream = await deleteJson(
        request,
        `${env.sourceBaseUrl}/streams/udp/${pipeline.streamId}`,
      );
      const deletedListener = await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/listeners/${pipeline.listenerId}`,
      );
      const listenerAfterDelete = await request.get(
        `${env.analysisBaseUrl}/analysis/listeners/${pipeline.listenerId}`,
      );

      pipeline.streamId = null;
      pipeline.listenerId = null;

      expect(stoppedStream.is_active).toBe(false);
      expect(deletedListener.deleted).toBe(true);
      expect(listenerAfterDelete.status()).toBe(404);
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });
});

function adaptiveTelemetry(overrides = {}) {
  return telemetryPayload({
    ground_speed_m_s: 0,
    vertical_speed_m_s: 0,
    velocity_x_m_s: 0,
    velocity_y_m_s: 0,
    velocity_z_m_s: 0,
    yaw_rad: 1.5708,
    message_quality: 1,
    ...overrides,
  });
}

function sourceForDetector(anomaly, detector) {
  return anomaly?.sources.find((source) => source.detector === detector);
}
