# E2E tests

End-to-end tests for the root `compose.yaml` stack.

## Scope

The automated set covers the current rule-based E2E scope without ML/NN
detectors. It includes 33 tests across backend API, UDP MAVLink ingestion,
synthetic telemetry streams, and viewer UI behavior.

- backend health checks;
- rule-based analysis session creation;
- manual normal telemetry analysis;
- manual low battery detection;
- manual GPS signal loss detection;
- manual impossible altitude detection;
- stateful battery drop detection;
- stateful GPS spoofing detection;
- stateful IMU spike detection;
- motion inconsistency detection;
- telemetry freeze detection;
- telemetry gap detection;
- disabled rule filtering;
- analysis session state isolation;
- UDP MAVLink listener creation;
- invalid UDP packet handling;
- session deletion listener cleanup;
- listener endpoint conflict handling;
- synthetic generator stream to analysis listener;
- GPS signal loss injection through the stream;
- GPS spoofing injection through the stream;
- IMU spike injection through the stream;
- battery drop injection through the stream;
- stream and listener cleanup;
- viewer dashboard loading;
- viewer empty rule-based state;
- viewer session rendering;
- viewer UDP listener status rendering;
- viewer live rule-based result rendering;
- viewer listener live counter updates;
- viewer GPS signal loss rendering;
- viewer detector output details;
- viewer rule-based profile control.

## Structure

```text
e2e-tests/
  package.json
  playwright.config.mjs
  tests/
    backend.e2e.spec.mjs
    viewer.e2e.spec.mjs
    support/
      api.mjs
```

- `backend.e2e.spec.mjs` covers service-to-service behavior, manual telemetry
  analysis, session state, UDP listeners, synthetic streams, and anomaly
  injections.
- `viewer.e2e.spec.mjs` covers the deployed telemetry viewer against real
  backend state created through the API.
- `support/api.mjs` contains shared HTTP, stream, telemetry payload, polling,
  cleanup, and UDP helper functions.

## Run

Start the repository services from the repository root:

```powershell
docker compose up --build -d --wait
```

Install the e2e module dependencies:

```powershell
cd e2e-tests
npm install
npm run install:browsers
```

Run all tests:

```powershell
npm test
```

Backend-only and viewer-only runs:

```powershell
npm run test:backend
npm run test:viewer
```

## Run In Docker

The same tests can run from a Playwright container attached to the Compose
network. This avoids local browser installation and matches the CI-style
environment more closely.

```powershell
docker run --rm `
  --network telemetry-analyser_default `
  --ipc=host `
  -v "${PWD}:/work" `
  -v telemetry-e2e-node-modules:/work/e2e-tests/node_modules `
  -w /work/e2e-tests `
  -e E2E_ANALYSIS_BASE_URL=http://analysis-service:8010 `
  -e E2E_TELEMETRY_SOURCE_BASE_URL=http://telemetry-source-backend:8000 `
  -e E2E_VIEWER_BASE_URL=http://telemetry-viewer `
  -e E2E_STREAM_TARGET_HOST=analysis-service `
  mcr.microsoft.com/playwright:v1.60.0-noble `
  sh -lc "npm ci && npm test"
```

The Compose network name is derived from the repository directory name. If your
Compose project uses another name, replace `telemetry-analyser_default`.

## Configuration

The tests use these defaults:

- `E2E_ANALYSIS_BASE_URL=http://127.0.0.1:8010`
- `E2E_TELEMETRY_SOURCE_BASE_URL=http://127.0.0.1:8000`
- `E2E_VIEWER_BASE_URL=http://127.0.0.1:3001`
- `E2E_STREAM_TARGET_HOST=analysis-service`
- `E2E_LISTENER_BIND_HOST=0.0.0.0`
- `E2E_LISTENER_BASE_PORT=14560`

For local non-Docker service processes, set `E2E_STREAM_TARGET_HOST=127.0.0.1`.

## Runtime Notes

- Tests run with one Playwright worker because several scenarios create UDP
  listeners and use deterministic listener ports.
- Each test creates its own sessions, listeners, missions, and streams, then
  cleans them up in `finally` blocks.
- Viewer tests create backend state through API calls, then verify what the UI
  renders from the deployed frontend.
- Playwright traces, screenshots, and videos are retained only on failure
  according to `playwright.config.mjs`.

## Not Covered

These tests intentionally do not cover ML/NN detectors, exhaustive threshold
boundary testing, long-duration load testing, persistence across process
restarts, or every malformed MAVLink frame variant. Those belong in focused
unit, integration, or load tests rather than the main E2E smoke/regression set.
