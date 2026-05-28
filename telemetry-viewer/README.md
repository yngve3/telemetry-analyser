# telemetry-viewer

Frontend application for telemetry observation and analysis result visualization.

The viewer is a separate React + Vite + TypeScript application. It does not
run anomaly detection itself and does not import Python code from backend
modules. Runtime interaction happens through HTTP APIs.

## Responsibilities

- display analysis profile settings;
- create and select analysis sessions;
- display session state with latest telemetry and analysis result;
- display aggregated anomalies and detector outputs.
- create, delete, and monitor analysis-service UDP listeners on a separate
  listener management page.
- switch UI language between English and Russian.

## Boundaries

The viewer talks to:

- `analysis-service` API;
- `telemetry-source` API for service health and future source controls.

The main polling endpoint for the dashboard is:

```text
GET /analysis/sessions/{session_id}/state
```

Listener transport management is separated from analysis workflows. The
`Listeners` page uses `/analysis/listeners` endpoints for listener lifecycle and
transport metrics.

The viewer must not depend on:

- `analysis-module`;
- `telemetry-converter`;
- Python backend code;
- MAVLink as an internal UI model.

## Running

From the repository root:

```powershell
docker compose up --build telemetry-viewer
```

The application is exposed at http://127.0.0.1:3001.

For frontend development:

```powershell
docker compose -f compose.dev.yaml up --build telemetry-viewer
```

## Documentation

- [Architecture](docs/architecture.md)
