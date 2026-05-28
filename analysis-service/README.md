# analysis-service

FastAPI backend that orchestrates telemetry analysis over `analysis-module` and
`telemetry-converter`.

The service owns HTTP, profile, and session concerns. It does not implement
anomaly detection or result aggregation. Detector execution, history updates,
aggregation, `sources`, and `detector_outputs` are handled by `analysis-module`.

## Runtime Flow

```text
HTTP request
-> unified telemetry or MAVLink payload
-> telemetry-converter, when needed
-> analysis-module analyzer
-> AnomalyResult.to_dict()
-> HTTP response
```

## API

- `GET /health`
- `GET /analysis/profile`
- `PUT /analysis/profile`
- `GET /analysis/detectors`
- `POST /analysis/sessions`
- `GET /analysis/sessions/{session_id}`
- `DELETE /analysis/sessions/{session_id}`
- `POST /analysis/sessions/{session_id}/analyze`
- `GET /analysis/sessions/{session_id}/state`
- `GET /analysis/sessions/{session_id}/last-telemetry`
- `GET /analysis/sessions/{session_id}/last-result`
- `POST /analysis/listeners`
- `GET /analysis/listeners`
- `GET /analysis/listeners/{listener_id}`
- `DELETE /analysis/listeners/{listener_id}`

`POST /analysis/sessions/{session_id}/analyze` accepts either
`unified.telemetry` with a telemetry object or `mavlink.v2` with a base64 payload.

`POST /analysis/listeners` starts an inbound listener. For UDP, `bind_host` and
`bind_port` are local bind settings for `analysis-service`; telemetry generators
must send MAVLink packets to that host and port.

Listener status is intended for transport metrics such as received packets,
converted samples, and listener errors. Viewers should treat
`GET /analysis/sessions/{session_id}/state` as the primary polling source for
dashboard data because it includes session metadata, the latest telemetry sample,
and the latest analysis result.

## Running Tests

From the repository root:

```powershell
python -B -m unittest discover -s analysis-service\tests
```
