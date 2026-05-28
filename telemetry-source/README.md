# telemetry-source

Application for producing and publishing UAV telemetry from configurable sources.

The module separates telemetry acquisition from data encoding and delivery. Source implementations produce telemetry payloads, encoders serialize those payloads, and transports deliver encoded data to downstream consumers.

## Structure

```text
backend/     # Python backend and source orchestration
frontend/    # source configuration UI
```

## Source Modes

- synthetic telemetry generation;
- snapshot upload and playback;
- connection to an external telemetry source.

The backend can run synthetic mission scripts, accept runtime commands, inject
synthetic anomalies, upload telemetry snapshots, send snapshots once, replay
snapshots as streams, receive external UDP telemetry packets, validate samples
against shared contracts, and publish MAVLink-over-UDP telemetry streams.

## Backend Boundaries

The backend follows a lightweight DDD structure:

- `domain` - source profiles, telemetry samples, source modes, publishing sessions, and domain rules;
- `application` - use cases and ports;
- `infrastructure` - concrete source, MAVLink encoder, UDP transport, contract validation, and persistence adapters;
- `presentation` - FastAPI routes and API schemas.

Application ports keep source configuration, encoding, and transport concerns independent from concrete infrastructure.

## Documentation

- [Module architecture](docs/architecture.md)
- [Synthetic mission script](docs/mission-script.md)
- [Synthetic anomaly injection](docs/anomaly-injection.md)
- [Snapshot source](docs/snapshot-source.md)
- [External source](docs/external-source.md)
- [Backend package layout](backend/README.md)
- [Frontend notes](frontend/README.md)

## Docker Compose

From the repository root:

```powershell
docker compose up --build
```

The compose stack starts:

- `telemetry-source-backend` on port `8000`;
- `telemetry-source-frontend` on port `3000`.

Backend Swagger UI is available at `http://127.0.0.1:8000/docs`.

For frontend development with Vite:

```powershell
docker compose -f compose.dev.yaml up --build
```
