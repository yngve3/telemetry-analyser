# E2E tests

End-to-end tests for the root `compose.yaml` stack.

## Scope

The first automated set covers:

- backend health checks;
- rule-based analysis session creation;
- manual normal telemetry analysis;
- manual low battery detection;
- stateful battery drop detection;
- UDP MAVLink listener creation;
- synthetic generator stream to analysis listener;
- GPS signal loss injection through the stream;
- stream and listener cleanup;
- viewer dashboard loading;
- viewer live rule-based result rendering;
- viewer GPS signal loss rendering.

## Run

Start the repository services from the root:

```powershell
docker compose up --build
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

## Configuration

The tests use these defaults:

- `E2E_ANALYSIS_BASE_URL=http://127.0.0.1:8010`
- `E2E_TELEMETRY_SOURCE_BASE_URL=http://127.0.0.1:8000`
- `E2E_VIEWER_BASE_URL=http://127.0.0.1:3001`
- `E2E_STREAM_TARGET_HOST=analysis-service`
- `E2E_LISTENER_BIND_HOST=0.0.0.0`
- `E2E_LISTENER_BASE_PORT=14560`

For local non-Docker service processes, set `E2E_STREAM_TARGET_HOST=127.0.0.1`.
