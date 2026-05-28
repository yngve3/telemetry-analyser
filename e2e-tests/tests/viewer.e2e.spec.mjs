import { expect, test } from "@playwright/test";

import {
  anomalyTypes,
  cleanupPipeline,
  env,
  injectAnomaly,
  startPipeline,
  waitForLastResult,
  waitForListenerSamples,
  waitForSessionState,
} from "./support/api.mjs";

test.describe("Viewer E2E", () => {
  test("viewer loads dashboard", async ({ page }) => {
    const consoleErrors = captureConsoleErrors(page);

    await openViewer(page);

    await expect(page.getByText("Telemetry Viewer")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Analysis" })).toBeVisible();
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
        page.getByText(state.last_telemetry.timestamp).first(),
      ).toBeVisible();
      await expect(page.getByText("rule_based").first()).toBeVisible();
      await expect(
        page.locator("section.data-panel", { hasText: "Anomaly results" }),
      ).toContainText(/No anomalies in the latest result\.|found|clear/);

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

      await expect(page.getByText("GPS_SIGNAL_LOSS").first()).toBeVisible();
      await expect(page.getByText("critical").first()).toBeVisible();
      await expect(page.getByText("rule_based").first()).toBeVisible();

      expect(consoleErrors).toEqual([]);
    } finally {
      await cleanupPipeline(request, pipeline);
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
