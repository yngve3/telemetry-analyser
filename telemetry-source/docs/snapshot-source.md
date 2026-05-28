# Snapshot Source

The snapshot source stores uploaded telemetry samples and publishes them without using synthetic mission logic.

## Modes

- `send_once` emits every stored sample exactly one time.
- `stream` replays stored samples with a configured interval or request-level frequency override.

## API

Upload a snapshot:

```text
POST /sources/snapshots
```

Send it once through MAVLink-over-UDP:

```text
POST /sources/snapshots/{snapshot_id}/send-once/udp
```

Replay it as a stream:

```text
POST /streams/snapshots/{snapshot_id}/udp
```

Stop replay:

```text
DELETE /streams/snapshots/udp/{stream_id}
```

## Boundary

Snapshot source owns uploaded telemetry playback only. It does not depend on mission scripts, synthetic phases, generator commands, or anomaly injectors.
