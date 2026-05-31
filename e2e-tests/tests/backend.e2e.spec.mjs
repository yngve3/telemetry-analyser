import { expect, test } from "@playwright/test";

import {
  analyzeTelemetry,
  anomalyTypes,
  cleanupPipeline,
  createAnalysisSession,
  createListener,
  deleteJson,
  env,
  findAnomaly,
  getJson,
  injectAnomaly,
  listenerPort,
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
      expect(anomaly.sources[0].evidence).toHaveProperty("implied_speed_m_s");
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
