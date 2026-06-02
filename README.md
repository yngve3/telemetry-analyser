# Telemetry Analyser

Telemetry Analyser is a monorepo for UAV telemetry analysis, source simulation, integration, and visualization.

The repository is organized as independent modules connected through shared contracts. Each module owns its own README and module-specific documentation. The root README provides repository-level navigation and links to cross-module architecture documents.

## Modules

| Module | Responsibility |
| --- | --- |
| [analysis-module](analysis-module/README.md) | Telemetry anomaly analysis domain and application logic |
| [analysis-service](analysis-service/README.md) | FastAPI runtime service for analysis profiles, sessions, and telemetry analysis |
| [telemetry-source](telemetry-source/README.md) | Configurable telemetry source application with backend and frontend |
| [telemetry-converter](telemetry-converter/README.md) | Telemetry integration boundary for conversion to `UnifiedTelemetry` |
| [telemetry-viewer](telemetry-viewer/README.md) | Telemetry and anomaly result visualization |
| [shared-contracts](shared-contracts/README.md) | JSON Schema contracts shared between modules |
| [e2e-tests](e2e-tests/README.md) | End-to-end tests for the full Docker Compose stack |

## Repository Documentation

- [Project architecture](docs/architecture.md)
- [Documentation structure](docs/documentation.md)
- [Static analysis and security checks](tools/static-analysis/README.md)

## Running Tests

Run the full repository check, including Python unit tests, frontend tests/builds,
Docker Compose startup, and Playwright E2E tests:

```powershell
bash tools/run-all-tests.sh
```

The task uses Python 3.11 by default. Override it if needed:

```powershell
PYTHON_VERSION=3.14 bash tools/run-all-tests.sh
```

Module-level unit and integration tests:

```powershell
python -B -m unittest discover -s analysis-module\tests
python -B -m unittest discover -s analysis-service\tests
python -B -m unittest discover -s telemetry-converter\tests
python -B -m unittest discover -s telemetry-source\backend\tests
```

End-to-end tests live in [e2e-tests](e2e-tests/README.md) and run against the
root Docker Compose stack. The current E2E scope covers rule-based analysis only
without ML/NN detectors.

```powershell
docker compose up --build -d --wait
cd e2e-tests
npm install
npm run install:browsers
npm test
```

To run E2E tests in a Playwright Docker container instead of installing local
browsers:

```powershell
docker run --rm `
  --network telemetry-analyser_default `
  --ipc=host `
  -v "${PWD}:/work" `
  -v telemetry-e2e-node-modules:/work/e2e-tests/node_modules `
  -w /work/e2e-tests `
  -e E2E_ANALYSIS_BASE_URL=http://analysis-service:8010 `
  -e E2E_TELEMETRY_SOURCE_BASE_URL=http://telemetry-source-backend:8000 `
  -e E2E_VIEWER_BASE_URL=http://telemetry-viewer `
  -e E2E_STREAM_TARGET_HOST=analysis-service `
  mcr.microsoft.com/playwright:v1.60.0-noble `
  sh -lc "npm ci && npm test"
```

The telemetry source backend includes synthetic mission execution, runtime anomaly injection, shared-contract telemetry validation, and continuous MAVLink-over-UDP publication.

## Running With Docker Compose

From the repository root:

```powershell
docker compose up --build
```

Services:

- analysis service: http://127.0.0.1:8010
- analysis service Swagger UI: http://127.0.0.1:8010/docs
- telemetry viewer: http://127.0.0.1:3001
- telemetry source frontend: http://127.0.0.1:3000
- telemetry source backend: http://127.0.0.1:8000
- backend Swagger UI: http://127.0.0.1:8000/docs
- telemetry source external UDP ingress: 0.0.0.0:14540/udp

Frontend development with the Vite dev server:

```powershell
docker compose -f compose.dev.yaml up --build
```
