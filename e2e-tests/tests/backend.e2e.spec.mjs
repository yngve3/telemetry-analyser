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
