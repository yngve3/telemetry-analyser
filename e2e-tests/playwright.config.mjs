import { defineConfig, devices } from "@playwright/test";

const viewerBaseUrl = process.env.E2E_VIEWER_BASE_URL ?? "http://127.0.0.1:3001";

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: viewerBaseUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "backend",
      testMatch: /backend\.e2e\.spec\.mjs/,
    },
    {
      name: "viewer",
      testMatch: /viewer\.e2e\.spec\.mjs/,
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
});
