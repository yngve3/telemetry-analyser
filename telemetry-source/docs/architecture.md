# telemetry-source Architecture

`telemetry-source` owns telemetry acquisition, generation, encoding, and publication.

## Application Shape

```text
telemetry-source/
  backend/
  frontend/
```

The backend contains source orchestration and delivery logic. The frontend provides configuration workflows for telemetry source modes.

## Backend Layers

```text
domain/
application/
infrastructure/
presentation/
```

- `domain` contains source profiles, source modes, telemetry samples, anomaly profiles, publishing sessions, and domain services.
- `application` contains use cases and ports.
- `infrastructure` contains concrete source, encoder, transport, contract validation, and persistence adapters.
- `presentation` contains FastAPI routes and API schemas.

## Domain Structure

```text
domain/
  common/      # models shared by all source modes
  synthetic/   # mission scripts, playback, commands, and synthetic anomalies
  snapshot/    # snapshot playback configuration and policies
  external/    # external source connection configuration and policies
```

`common` contains only concepts shared by all source modes: `TelemetrySample`, `SourceMode`, `SourceProfile`, and `PublishingSession`.

Synthetic mission planning is intentionally isolated in `domain/synthetic`. Snapshot and external sources do not depend on mission scripts, mission phases, mission commands, or anomaly injection.

## Source Workflows

- configure synthetic telemetry generation;
- upload and send or replay a telemetry snapshot;
- connect to an external telemetry source.

## Runtime Pipeline

```text
TelemetrySource -> TelemetryEncoder -> TelemetryTransport
```

The pipeline is assembled outside the domain layer. Concrete adapters are selected by presentation/application orchestration, while source modes keep producing domain telemetry samples.

## Synthetic Source

The synthetic source is a mission playback engine:

```text
MissionScript
-> MissionScriptCompiler
-> MissionPlan
-> MissionRunner
-> TelemetrySample
-> active anomaly injectors
```

It owns human-friendly mission scripts, normalized flight phases, runtime commands, parameter overrides, and scheduled anomaly injection.

`MissionScript` is the input format for UI and JSON import/export. `MissionPlan` is the executable runtime format consumed by the generator.

The generator core is deterministic by mission time: `SyntheticTelemetryFactory` can create a `TelemetrySample` for a given `MissionPlan` and elapsed time, while `MissionRunner` manages mutable playback state and runtime commands.

The motion model is intentionally compact. Climb, descent, yaw, acceleration, battery drain, and noise are represented by profile objects on the mission plan. Horizontal movement uses a trapezoidal or triangular acceleration profile instead of plain linear progress. Runtime `target_speed` changes recalculate movement durations and affect the generated trajectory.

The FastAPI presentation layer exposes the generator through `/sources/synthetic/missions` endpoints. Swagger UI is available at `/docs`.

## Contract Validation

Samples leaving the backend are validated against `shared-contracts/telemetry.schema.json`.

The validator lives in infrastructure because JSON Schema is an exchange contract, not the internal domain model. Domain services operate on `TelemetrySample`; API mappers and stream publishers validate serialized samples before exposing them to other modules.

## MAVLink-over-UDP Publication

Continuous publication is available through:

```text
POST /streams/synthetic/missions/{mission_id}/udp
DELETE /streams/udp/{stream_id}
```

The streaming pipeline is:

```text
MissionRunner
-> TelemetrySample
-> shared-contract validation
-> MavlinkTelemetryEncoder
-> UdpTelemetryTransport
```

The MAVLink adapter encodes `TelemetrySample` as a focused MAVLink v2 telemetry subset:

- `HEARTBEAT` for vehicle state, arming state, system status, and flight mode;
- `ATTITUDE` for roll, pitch, yaw, and angular rates;
- `GLOBAL_POSITION_INT` for global position, velocity, altitude, and heading;
- `GPS_RAW_INT` for GPS fix type, satellite count, coordinates, and GPS quality;
- `SYS_STATUS` for battery and sensor health state.

MAVLink remains an infrastructure format and does not appear in synthetic mission domain logic.

## Snapshot Source

The snapshot source reads existing telemetry samples and emits them according to playback mode:

- send once;
- replay as a stream.

Uploaded snapshot samples are validated against `shared-contracts/telemetry.schema.json`. Send-once publication emits every sample exactly once through the injected MAVLink-over-UDP pipeline. Stream replay uses `SnapshotCursor` and can either stop after the last sample or repeat from the beginning.

It does not use mission plans or synthetic anomaly injection.

## External Source

The external source is a raw telemetry ingress boundary. It listens for UDP packets from an upstream telemetry producer and tracks connection status, received packet count, received byte count, and last packet metadata.

The external source does not decode MAVLink into `TelemetrySample`; MAVLink decoding belongs to `telemetry-converter`. This keeps the source backend responsible for acquisition and connection lifecycle, while conversion to `UnifiedTelemetry` remains in the integration module.

It does not use mission plans, snapshot cursors, or synthetic anomaly injection.
