# telemetry-source frontend

Web UI for configuring telemetry sources and publishing modes.

## Workflows

- configure synthetic telemetry generation;
- upload a snapshot and send it once or replay it as a stream;
- connect to an external source by address, port, and protocol.

## Stack

- React;
- TypeScript;
- Vite;
- TanStack Query;
- typed fetch wrappers over the backend HTTP API.

The frontend does not import Python code. Backend communication goes through
HTTP endpoints exposed by `telemetry-source/backend`.

## Local Development

```powershell
npm install
npm run dev
```

The Vite server runs on:

```text
http://127.0.0.1:3000
```

By default API calls go to `/api`, which Vite proxies to
`http://127.0.0.1:8000`. Override the dev proxy target with:

```powershell
$env:VITE_DEV_API_PROXY_TARGET="http://127.0.0.1:8000"
```

Use `VITE_API_BASE_URL` only when the backend is exposed through a same-origin
proxy or has CORS configured for the frontend origin.

## Docker

The container builds the Vite app and serves `dist` through nginx. Root
`compose.yaml` starts it together with the backend:

```powershell
docker compose up --build
```

URL:

```text
http://127.0.0.1:3000
```

Dev compose with Vite:

```powershell
docker compose -f compose.dev.yaml up --build
```
