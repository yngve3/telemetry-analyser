# External Source

The external source mode receives telemetry from an upstream system without using generator or snapshot playback logic.

## Transport

The backend supports UDP ingestion. A registered external source defines:

- source name;
- bind address;
- bind port;
- protocol.

In Docker Compose the backend publishes UDP port `14540`. For packets sent from
another process or VM to the host machine, register the source with:

```json
{
  "name": "external_mavlink",
  "address": "0.0.0.0",
  "port": 14540,
  "protocol": "udp"
}
```

The upstream sender should target the host computer address, for example
`<PC_IP>:14540`. Do not use `127.0.0.1` unless the sender runs inside the same
backend process namespace.

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
