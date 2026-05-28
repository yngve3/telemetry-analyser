# telemetry-viewer Architecture

`telemetry-viewer` is a frontend-only UI for telemetry observation and runtime
analysis control.

## Boundary

The viewer consumes backend APIs and shared HTTP contracts. It must not import
Python code from `analysis-module`, `analysis-service`, `telemetry-converter`,
or `telemetry-source`.

MAVLink is treated as an external transport format. The UI works with analysis
sessions, listener metadata, unified telemetry payloads, aggregated anomalies,
and detector outputs.

## Runtime APIs

- `analysis-service`:
  - health;
  - detector discovery;
  - analysis profile;
  - analysis sessions;
  - UDP listeners;
  - analysis session state.
- `telemetry-source`:
  - health;
  - future source and stream controls.

## Current Dashboard

### Analysis Page

- analysis profile controls;
- session creation and selection;
- manual unified telemetry analysis;
- telemetry overview;
- anomaly result table;
- detector output panels;
- recent result history.

### Listeners Page

- listener creation for an existing analysis session;
- listener deletion;
- listener selection;
- transport metrics polling;
- last listener result inspection.

## Polling Model

The dashboard polls `GET /analysis/sessions/{session_id}/state` for session
metadata, `last_telemetry`, and `last_result`. Listener endpoints are used for
transport metrics such as packets, bytes, converted samples, and errors.
