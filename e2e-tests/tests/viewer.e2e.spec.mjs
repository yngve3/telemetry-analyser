import { expect, test } from "@playwright/test";

import {
  adaptiveCorrelationProfile,
  analyzeTelemetry,
  anomalyTypes,
  cleanupPipeline,
  createAnalysisSession,
  createListener,
  deleteJson,
  env,
  getJson,
  injectAnomaly,
  listenerPort,
  ruleBasedProfile,
  startPipeline,
  telemetryPayload,
  uniqueId,
  waitForLastResult,
  waitForListenerSamples,
  waitForSessionState,
  waitForValue,
} from "./support/api.mjs";

test.describe("Viewer E2E", () => {
  test("viewer loads dashboard", async ({ page }) => {
    const consoleErrors = captureConsoleErrors(page);

    await openViewer(page);

    await expect(page.getByText("Telemetry Viewer")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Analysis", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Session panel" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Anomaly results" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Detector outputs" }),
    ).toBeVisible();
    await page.waitForTimeout(500);

    expect(consoleErrors).toEqual([]);
  });

  test("viewer shows empty rule-based state", async ({ page }) => {
    await openViewer(page);

    await expect(page.getByText("Rules").first()).toBeVisible();
    await expect(page.getByText("No analysis result yet.")).toBeVisible();
    await expect(page.getByText("No detector output yet.")).toBeVisible();
  });

  test("viewer shows analysis session", async ({ page, request }) => {
    const sessionId = uniqueId("viewer-session");

    try {
      await createAnalysisSession(request, {
        sessionId,
        profile: ruleBasedProfile(),
      });

      await openViewer(page);
      await selectSession(page, sessionId);

      const sessionPanel = page.locator("section.data-panel", {
        hasText: "Session panel",
      });
      await expect(sessionPanel).toContainText(sessionId);
      await expect(sessionPanel).toContainText("0");
      await expect(
        page.locator("section.data-panel", { hasText: "Analysis profile" }),
      ).toContainText("1 enabled");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("viewer shows UDP listener status", async (
    { page, request },
    testInfo,
  ) => {
    const sessionId = uniqueId("viewer-listener");
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
        "viewer listener to become active",
      );

      await openViewer(page);
      await page.getByRole("button", { name: "Listeners" }).click();
      await expect(page.getByText(listenerId).first()).toBeVisible();
      await page.getByRole("button", { name: listenerId }).click();

      const listenerState = page.locator("section.data-panel", {
        hasText: "Listener state",
      });
      await expect(listenerState).toContainText("active");
      await expect(listenerState).toContainText("0.0.0.0");
      await expect(listenerState).toContainText(String(port));
      await expect(listenerState).toContainText("Packets");
      await expect(listenerState).toContainText("Converted");
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

  test("viewer shows live rule-based result", async (
    { page, request },
    testInfo,
  ) => {
    const pipeline = await startPipeline(request, testInfo);
    const consoleErrors = captureConsoleErrors(page);

    try {
      await waitForListenerSamples(request, pipeline.listenerId);
      const state = await waitForSessionState(
        request,
        pipeline.sessionId,
        (payload) =>
          Boolean(payload.last_result?.detector_outputs?.rule_based) &&
          Boolean(payload.last_telemetry),
      );

      await openViewer(page);
      await selectSession(page, pipeline.sessionId);

      await expect(page.getByText(pipeline.sessionId).first()).toBeVisible();
      await expect(
        page.getByText(state.last_telemetry.drone_id).first(),
      ).toBeVisible();
      await expect(
        page.locator("section.data-panel", { hasText: "Telemetry overview" }),
      ).toContainText(/\d{4}-\d{2}-\d{2}T/);
      await expect(page.getByText("Rules").first()).toBeVisible();
      await expect(
        page.locator("section.data-panel", { hasText: "Anomaly results" }),
      ).toContainText(/No anomalies in the latest result\.|found|clear/);

      expect(consoleErrors).toEqual([]);
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("viewer updates listener counters live", async (
    { page, request },
    testInfo,
  ) => {
    const pipeline = await startPipeline(request, testInfo);
    const consoleErrors = captureConsoleErrors(page);

    try {
      await waitForListenerSamples(request, pipeline.listenerId);

      await openViewer(page);
      await page.getByRole("button", { name: "Listeners" }).click();
      await expect(page.getByText(pipeline.listenerId).first()).toBeVisible();
      await page.getByRole("button", { name: pipeline.listenerId }).click();

      const listenerState = page.locator("section.data-panel", {
        hasText: "Listener state",
      });
      const initialPackets = await metricValue(listenerState, "Packets");
      const initialConverted = await metricValue(listenerState, "Converted");

      await expect
        .poll(() => metricValue(listenerState, "Packets"), {
          timeout: 6_000,
        })
        .toBeGreaterThan(initialPackets);
      await expect
        .poll(() => metricValue(listenerState, "Converted"), {
          timeout: 6_000,
        })
        .toBeGreaterThan(initialConverted);

      expect(consoleErrors).toEqual([]);
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("viewer shows injected GPS signal loss", async (
    { page, request },
    testInfo,
  ) => {
    const pipeline = await startPipeline(request, testInfo);
    const consoleErrors = captureConsoleErrors(page);

    try {
      await waitForListenerSamples(request, pipeline.listenerId);
      await injectAnomaly(request, pipeline.missionId, "GPS_SIGNAL_LOSS");
      await waitForLastResult(request, pipeline.sessionId, (payload) =>
        anomalyTypes(payload).includes("GPS_SIGNAL_LOSS"),
      );

      await openViewer(page);
      await selectSession(page, pipeline.sessionId);

      await expect(page.getByText("GPS signal loss").first()).toBeVisible();
      await expect(page.getByText("critical").first()).toBeVisible();
      await expect(page.getByText("Rules").first()).toBeVisible();

      expect(consoleErrors).toEqual([]);
    } finally {
      await cleanupPipeline(request, pipeline);
    }
  });

  test("viewer shows detector output details", async ({ page, request }) => {
    const sessionId = uniqueId("viewer-details");

    try {
      await createAnalysisSession(request, {
        sessionId,
        profile: ruleBasedProfile(),
      });
      await analyzeTelemetry(
        request,
        sessionId,
        telemetryPayload({ battery_percent: 10 }),
      );

      await openViewer(page);
      await selectSession(page, sessionId);

      const detectorPanel = page.locator("section.data-panel", {
        hasText: "Detector outputs",
      });
      await expect(detectorPanel).toContainText("Rules");
      await expect(detectorPanel).toContainText("Low battery");
      await expect(detectorPanel).toContainText(/50%|100%/);
      await detectorPanel.getByText("Evidence").click();
      await expect(detectorPanel).toContainText("Battery, %");
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("viewer renders adaptive correlation output and timing", async ({
    page,
    request,
  }) => {
    const sessionId = uniqueId("viewer-adaptive");
    const consoleErrors = captureConsoleErrors(page);

    try {
      await createAnalysisSession(request, {
        sessionId,
        profile: adaptiveCorrelationProfile(),
      });
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

      await openViewer(page);
      await selectSession(page, sessionId);

      const detectorPanel = page.locator("section.data-panel", {
        hasText: "Detector outputs",
      });
      await expect(detectorPanel).toContainText("Adaptive correlation");
      await expect(detectorPanel).toContainText("No detector anomalies.");

      const timingPanel = page.locator("section.data-panel", {
        hasText: "Analysis timing",
      });
      await expect(timingPanel).toContainText("Total time");
      await expect(timingPanel).toContainText("Rules");
      await expect(timingPanel).toContainText("Adaptive correlation");
      await expect(timingPanel).toContainText(/ms|<1 ms/);

      expect(consoleErrors).toEqual([]);
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("viewer renders aggregated adaptive correlation sources", async ({
    page,
    request,
  }) => {
    const sessionId = uniqueId("viewer-adaptive-sources");
    const consoleErrors = captureConsoleErrors(page);

    try {
      await createAnalysisSession(request, {
        sessionId,
        profile: adaptiveCorrelationProfile({
          enabled_rules: ["motion_inconsistency"],
        }),
      });
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
          latitude_deg: 47.399742,
          ground_speed_m_s: 1,
          velocity_x_m_s: 20,
          velocity_y_m_s: 0,
        }),
      );

      await openViewer(page);
      await selectSession(page, sessionId);

      const anomalyPanel = page.locator("section.data-panel", {
        hasText: "Anomaly results",
      });
      await expect(anomalyPanel).toContainText("Motion inconsistency");
      await expect(anomalyPanel).toContainText("Rules");
      await expect(anomalyPanel).toContainText("Adaptive correlation");
      await anomalyPanel.getByText("Detector contribution").click();
      await expect(anomalyPanel).toContainText("Position-speed error");
      await expect(anomalyPanel).toContainText("Exceeded errors");

      expect(consoleErrors).toEqual([]);
    } finally {
      await deleteJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}`,
      );
    }
  });

  test("viewer profile toggle rule-based", async ({ page, request }) => {
    await request.put(`${env.analysisBaseUrl}/analysis/profile`, {
      data: ruleBasedProfile(),
    });

    try {
      await openViewer(page);

      const analyzersPanel = page.locator("section.data-panel", {
        hasText: "Analyzers",
      });
      const ruleBasedButton = analyzersPanel.getByRole("button", {
        name: /Rules/,
      });

      await expect(ruleBasedButton).toHaveAttribute("aria-pressed", "true");
      await ruleBasedButton.click();
      await expect(ruleBasedButton).toHaveAttribute("aria-pressed", "false");
      await ruleBasedButton.click();
      await expect(ruleBasedButton).toHaveAttribute("aria-pressed", "true");

      await Promise.all([
        page.waitForResponse(
          (response) =>
            response.url().includes("/analysis/profile") &&
            response.request().method() === "PUT" &&
            response.ok(),
        ),
        analyzersPanel.getByRole("button", { name: "Save analyzers" }).click(),
      ]);

      const profile = await getJson(
        request,
        `${env.analysisBaseUrl}/analysis/profile`,
      );
      expect(profile.enabled_detectors).toEqual(["rule_based"]);
      await expect(ruleBasedButton).toHaveAttribute("aria-pressed", "true");
    } finally {
      await request.put(`${env.analysisBaseUrl}/analysis/profile`, {
        data: ruleBasedProfile(),
      });
    }
  });
});

async function openViewer(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("telemetry-viewer-language", "en");
  });
  await page.goto(env.viewerBaseUrl);
  await page.waitForLoadState("networkidle");
}

async function selectSession(page, sessionId) {
  await page.getByLabel("Session ID").fill(sessionId);
  await page.getByRole("button", { name: "Select" }).click();
  await expect(page.locator(".session-metrics")).toContainText(sessionId);
}

function captureConsoleErrors(page) {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    errors.push(error.message);
  });
  return errors;
}

async function metricValue(container, label) {
  const text = await container
    .locator(".metric", { hasText: label })
    .locator("strong")
    .first()
    .textContent();
  return Number(text ?? 0);
}

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
