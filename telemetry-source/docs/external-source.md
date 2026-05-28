# External Source

The external source mode receives telemetry from an upstream system without using generator or snapshot playback logic.

## Transport

The backend supports UDP ingestion. A registered external source defines:

- source name;
- bind address;
- bind port;
- protocol.

## API

Register a source:

```text
POST /sources/external
```

Start receiving packets:

```text
POST /sources/external/{source_id}/start
```

Stop receiving packets:

```text
POST /sources/external/{source_id}/stop
```

Read status:

```text
GET /sources/external/{source_id}
```

## Boundary

External source is a raw ingress boundary. It tracks packet counters and last packet metadata, but it does not decode MAVLink or create `TelemetrySample` objects. MAVLink-to-`UnifiedTelemetry` conversion belongs to `telemetry-converter`.
