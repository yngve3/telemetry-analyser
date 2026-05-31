#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

export MYPYPATH="analysis-module/src:analysis-service/src:telemetry-converter/src:telemetry-source/backend/src"

ruff check --config tools/static-analysis/configs/ruff.toml \
  analysis-module/src \
  analysis-service/src \
  telemetry-converter/src \
  telemetry-source/backend/src

mypy --config-file tools/static-analysis/configs/mypy.ini \
  analysis-module/src \
  analysis-service/src \
  telemetry-converter/src \
  telemetry-source/backend/src

npm ci --prefix telemetry-viewer/frontend
npm run --prefix telemetry-viewer/frontend typecheck
npm run --prefix telemetry-viewer/frontend lint
