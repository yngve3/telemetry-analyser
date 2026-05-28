# telemetry-converter

Integration module for converting external telemetry payloads into the internal `UnifiedTelemetry` contract.

This module isolates transport and format-specific parsing from the domain logic in `analysis-module`.
MAVLink is the currently supported input format; other inputs can be added as separate adapters.

Conversion flow:

```text
External telemetry payload -> input adapter -> converter -> UnifiedTelemetry
```

Input transports and serialization formats remain integration concerns. They must not become part of the analysis domain model.

## Supported Formats

| Source format | Target format |
| --- | --- |
| `mavlink.v2` | `unified.telemetry` |
| `mavlink.v2` | `unified.telemetry.dict` |

## Library Usage

The package is intended to be used as a library by a runtime service, for example a future `analysis-service`.

```python
from telemetry_converter import TelemetryInputFormat, default_converter

converter = default_converter()
telemetry = converter.convert(
    mavlink_payload,
    source_format=TelemetryInputFormat.MAVLINK_V2,
)
```

For MAVLink-over-UDP streams where message types arrive with different rates, use the stateful stream decoder:

```python
from telemetry_converter import default_mavlink_stream_decoder

decoder = default_mavlink_stream_decoder()

for mavlink_packet in packets:
    telemetry = decoder.update(mavlink_packet)
    if telemetry is not None:
        analyze(telemetry)
```

For dependency injection, instantiate `TelemetryConverter` with explicit input decoders and output encoders instead of importing infrastructure details into domain code.

## Documentation

- [Architecture](docs/architecture.md)
