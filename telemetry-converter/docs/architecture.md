# telemetry-converter Architecture

`telemetry-converter` owns conversion from external telemetry payloads to the internal telemetry contract.

## Responsibility

The module maps external telemetry data into `UnifiedTelemetry`-compatible payloads. It does not define the analysis domain model.

MAVLink is implemented as the first input adapter because `telemetry-source` currently publishes MAVLink-over-UDP. Future inputs, such as WebSocket JSON, should be added as independent adapters without changing analysis code.

## Boundary

Transport-specific message structures, parsing, and field mapping belong in this module. The analysis domain receives only unified telemetry data.

The current runtime path is:

```text
MAVLink v2 bytes -> MavlinkV2TelemetryDecoder -> TelemetryConverter -> UnifiedTelemetry
```

New formats should implement the decoder port and be registered in the converter by source format.

MAVLink-over-UDP streams can deliver message types at different rates. The stateful stream decoder stores the latest values from slower messages and emits `UnifiedTelemetry` only after the required contract fields are available.

## Library Boundary

The module is packaged as a Python library with a `src/` layout. Public imports are intentionally kept small in `telemetry_converter.__init__`; infrastructure adapters remain in their own subpackages and should be wired from a service composition layer.
