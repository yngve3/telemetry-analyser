# telemetry-source backend

Python backend for configuring telemetry sources and publishing telemetry streams.

## Package Layout

```text
src/telemetry_source_backend/
  domain/
    common/      # models shared by all source modes
    synthetic/   # mission scripts, playback, commands, and anomaly injection
    snapshot/    # snapshot playback model and policies
    external/    # external source connection model and policies
  application/
    use_cases/   # source configuration and publishing scenarios
    ports/       # contracts required by use cases
  infrastructure/
    sources/     # synthetic, snapshot, and external source adapters
    encoders/    # MAVLink encoder adapter
    transports/  # UDP transport adapter
    persistence/ # repository implementations
  presentation/
    api/         # FastAPI application, routes, request/response schemas
```

## Runtime Model

```text
TelemetrySource -> TelemetryEncoder -> TelemetryTransport
```

The presentation layer exposes source configuration through FastAPI. Application use cases depend on ports, while infrastructure adapters provide concrete implementations.

The synthetic source provides the generator core:

```text
MissionScript -> MissionPlan -> MissionRunner -> TelemetrySample
```

Generated telemetry is validated against `shared-contracts/telemetry.schema.json`
before it is returned by API mappers or published as a stream.

Uploaded snapshots follow the same contract and publication pipeline:

```text
Snapshot -> TelemetrySample -> TelemetryFrameEncoder -> TelemetryTransport
```

## Running the Backend

From this directory:

```powershell
python -m uvicorn telemetry_source_backend.presentation.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

With Docker Compose from the repository root:

```powershell
docker compose up --build telemetry-source-backend
```

## Synthetic Generator API

Main endpoints:

- `POST /sources/synthetic/missions` - create a mission from `MissionScript`;
- `GET /sources/synthetic/missions` - list missions;
- `GET /sources/synthetic/missions/{mission_id}` - get mission status;
- `POST /sources/synthetic/missions/{mission_id}/start` - start mission playback;
- `POST /sources/synthetic/missions/{mission_id}/pause` - pause playback;
- `POST /sources/synthetic/missions/{mission_id}/resume` - resume playback;
- `POST /sources/synthetic/missions/{mission_id}/stop` - stop and reset playback;
- `POST /sources/synthetic/missions/{mission_id}/commands` - submit runtime command;
- `GET /sources/synthetic/missions/{mission_id}/sample` - get current sample;
- `POST /sources/synthetic/missions/{mission_id}/sample/next` - advance and get next sample;
- `GET /sources/synthetic/missions/{mission_id}/samples` - generate a sample batch;
- `POST /streams/synthetic/missions/{mission_id}/udp` - publish a continuous MAVLink-over-UDP stream;
- `GET /streams/udp` - list active and stopped UDP publication streams;
- `GET /streams/udp/{stream_id}` - get UDP stream status;
- `DELETE /streams/udp/{stream_id}` - stop UDP publication.

The stream endpoint encodes each telemetry sample as a MAVLink v2 telemetry subset and sends each frame through UDP. The subset is:

- `HEARTBEAT`;
- `ATTITUDE`;
- `GLOBAL_POSITION_INT`;
- `GPS_RAW_INT`;
- `SYS_STATUS`.

It uses the mission frequency by default, or an explicit `frequency_hz` from the stream request. Stream `sent_count` counts emitted MAVLink frames.

Example stream request:

```json
{
  "host": "analysis-service",
  "port": 14560,
  "frequency_hz": 20
}
```

## Snapshot API

Main endpoints:

- `POST /sources/snapshots` - upload a telemetry snapshot as JSON samples;
- `GET /sources/snapshots` - list uploaded snapshots;
- `GET /sources/snapshots/{snapshot_id}` - get snapshot status;
- `GET /sources/snapshots/{snapshot_id}/samples` - read snapshot samples;
- `POST /sources/snapshots/{snapshot_id}/send-once/udp` - send all snapshot samples once through MAVLink-over-UDP;
- `POST /streams/snapshots/{snapshot_id}/udp` - replay a snapshot as a MAVLink-over-UDP stream;
- `GET /streams/snapshots/udp` - list snapshot UDP streams;
- `GET /streams/snapshots/udp/{stream_id}` - get snapshot stream status;
- `DELETE /streams/snapshots/udp/{stream_id}` - stop snapshot stream.

Snapshot replay uses `interval_seconds` from the uploaded snapshot by default. A stream request can override playback frequency with `frequency_hz` and repeat behavior with `repeat`.

## External Source API

External sources are modeled as raw telemetry ingress. The backend listens for UDP packets from an upstream telemetry producer and records connection status, packet count, byte count, and last packet metadata.

Main endpoints:

- `POST /sources/external` - register an external UDP source;
- `GET /sources/external` - list external sources;
- `GET /sources/external/{source_id}` - get external source status;
- `POST /sources/external/{source_id}/start` - start UDP packet ingestion;
- `POST /sources/external/{source_id}/stop` - stop UDP packet ingestion.

External source ingestion does not decode MAVLink into `TelemetrySample`. MAVLink conversion belongs to the `telemetry-converter` boundary.

## Synthetic Motion Model

The generator uses a deliberately small motion model:

- takeoff and landing use configured climb/descent rates;
- waypoint and return-home phases use a trapezoidal or triangular acceleration profile;
- turns use a configured yaw rate;
- battery drain is calculated from phase-specific rates;
- optional deterministic noise can be applied to GPS position, altitude, speed, heading, and battery.

`set_parameter` with `target_speed` recalculates movement phase durations. For the active movement phase it uses the remaining distance; for future movement phases it uses the full phase distance.

## Source Boundaries

The backend keeps source modes isolated from each other:

- synthetic source owns mission scripts, mission playback, commands, and synthetic anomalies;
- snapshot source owns uploaded telemetry replay rules;
- external source owns upstream connection configuration.

The active API surface includes synthetic mission playback, snapshot upload, snapshot send-once publication, snapshot replay streams over MAVLink-over-UDP, and external UDP packet ingestion.

## Documentation

- [telemetry-source architecture](../docs/architecture.md)
- [Synthetic mission script](../docs/mission-script.md)
- [Synthetic anomaly injection](../docs/anomaly-injection.md)
- [Snapshot source](../docs/snapshot-source.md)
- [External source](../docs/external-source.md)
