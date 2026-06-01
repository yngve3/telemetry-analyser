# Project Architecture

## Overview

The project is organized as a monorepo of independent modules for UAV telemetry anomaly analysis. The core module accepts unified telemetry data and returns anomaly detection results.

The system is not tied to a specific telemetry source, transport protocol, UI, or data exchange format. MAVLink is treated as an external integration format, not as an internal domain model.

## Data Flow

```text
Telemetry source
-> encoder / transport
-> converter / adapter
-> UnifiedTelemetry
-> analysis-module
-> AnomalyResult
-> viewer / storage / API
```

## Modules

### analysis-module

Owns the telemetry analysis domain and application logic. It contains the domain model for telemetry samples, anomalies, severity levels, and analysis results.

The module does not depend on:

- MAVLink;
- telemetry source application;
- viewer;
- transport layer;
- data delivery mechanism.

The module works with `UnifiedTelemetry` and returns `AnomalyResult`. Analyzer implementations are application-layer services over the domain model.

Detector results are aggregated inside the module. A diagnostic layer enriches
final anomalies with `probable_cause`, `cause_confidence`,
`diagnostic_evidence`, and `recommended_action`.

Adaptive detectors that maintain a normal-behavior profile update that profile
only after the final aggregated result confirms that the current telemetry sample
is not anomalous. Static safety thresholds remain active before calibration is
complete.

### telemetry-converter

Owns conversion from external telemetry payloads into the internal `UnifiedTelemetry` format.

MAVLink is the currently implemented input adapter. It is not the system's internal model and must not leak into the domain logic of `analysis-module`.

### telemetry-source

Owns telemetry source configuration and publication. It is structured as an application with a Python backend and a web frontend.

The backend uses a lightweight DDD structure:

- `domain/common` - source profiles, source modes, telemetry samples, publishing sessions, and shared source concepts;
- `domain/synthetic` - mission scripts, mission plans, mission phases, runtime commands, parameter overrides, and synthetic anomaly injection;
- `domain/snapshot` - snapshot playback configuration and policies;
- `domain/external` - external source connection configuration and policies;
- `application` - source configuration and publishing use cases;
- `application/ports` - contracts required by use cases, such as `TelemetrySource`, `TelemetryEncoder`, `TelemetryTransport`, and `SourceRepository`;
- `infrastructure` - concrete source, encoder, transport, contract validation, and persistence adapters;
- `presentation` - FastAPI routes and request/response schemas.

The source application is structured around three source modes:

- synthetic telemetry generation;
- snapshot upload and playback;
- connection to an external telemetry source.

Source implementations, encoders, and transports are independent concerns. Synthetic mission logic is isolated from snapshot and external source logic. Domain and application logic do not depend on MAVLink, JSON, UDP, WebSocket, FastAPI, or any other infrastructure detail.

The source backend publishes synthetic missions and uploaded snapshots as MAVLink-over-UDP telemetry. It can also receive external UDP telemetry packets as a raw ingress boundary. Generated and uploaded samples are validated against `shared-contracts/telemetry.schema.json` before API exposure or stream publication.

The MAVLink stream uses a focused telemetry subset: `HEARTBEAT`, `ATTITUDE`, `GLOBAL_POSITION_INT`, `GPS_RAW_INT`, and `SYS_STATUS`.

### analysis-service

Owns runtime analysis orchestration over HTTP. The service manages analysis
profiles and stateful sessions, accepts unified telemetry or MAVLink payloads,
uses `telemetry-converter` when conversion is needed, calls `analysis-module`,
and returns the module-produced `AnomalyResult`.

The service can also open inbound listeners. For MAVLink-over-UDP, the service
binds a local UDP port and telemetry generators send packets to that endpoint.
In Docker Compose, generators should target the service DNS name, such as
`analysis-service:14560`, not `localhost`.

The service does not implement detector logic or result aggregation. Detector
execution, telemetry history updates, final `anomalies`, `sources`, and raw
`detector_outputs` remain responsibilities of `analysis-module`.

### telemetry-viewer

Displays incoming telemetry and analysis results.

The viewer must not import Python code from `analysis-module` directly. Interaction should happen through shared contracts from `shared-contracts`.

### shared-contracts

Directory for shared JSON Schema contracts:

- `telemetry.schema.json` - unified telemetry format;
- `anomaly-result.schema.json` - analysis result format;
- `flight-scenario.schema.json` - portable synthetic scenario format;
- `telemetry-source-config.schema.json` - source mode and publication format.

`telemetry.schema.json` includes freshness fields emitted by stream converters:
`attitude_age_ms`, `position_age_ms`, `gps_age_ms`, `system_age_ms`, and
`message_quality`.

## DDD Approach

DDD is used as a way to separate analysis domain logic from integrations and infrastructure.

`analysis-module` uses a lightweight split:

- `domain` - domain models for telemetry, anomalies, and analysis results;
- `application` - analyzer interface and rule-based analysis use case.

The project uses DDD only where it improves maintainability. The design avoids unnecessary aggregates, event sourcing, CQRS, and excessive abstraction.

`telemetry-source` uses the same principle with stronger boundaries because it coordinates multiple source modes and delivery mechanisms. Its source configuration and publishing concepts live in the domain and application layers; concrete adapters live in infrastructure and presentation.

Synthetic anomaly injection in `telemetry-source` is modeled as a domain extension point. New anomaly types are added as injectors behind an `AnomalyInjector` contract and registered in the anomaly registry.

Synthetic movement is modeled by configurable motion, battery, and noise profiles. This keeps the generator more realistic than linear interpolation while avoiding a full flight dynamics simulator.

## Extension Points

The module boundaries support these extension points:

- telemetry converter input adapters;
- MAVLink encoder/decoder;
- JSON, CSV, or log encoders;
- WebSocket/API layer;
- Docker Compose;
- separate `analysis-service`;
- viewer built with any suitable stack.

The core analysis domain logic can remain independent from infrastructure.
