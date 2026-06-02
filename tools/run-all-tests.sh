#!/usr/bin/env bash
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_CACHE_DIR="${UV_CACHE_DIR:-/private/tmp/uv-cache}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
COMPOSE_NETWORK="${COMPOSE_NETWORK:-telemetry-analyser_default}"
PLAYWRIGHT_IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.60.0-noble}"
NODE_IMAGE="${NODE_IMAGE:-node:24-alpine}"

PASSED_STEPS=()
FAILED_STEPS=()

run_step() {
  local name="$1"
  shift

  printf '\n'
  printf '========================================================================\n'
  printf 'RUNNING: %s\n' "$name"
  printf '========================================================================\n'

  if "$@"; then
    PASSED_STEPS+=("$name")
    printf '\nPASS: %s\n' "$name"
  else
    local status=$?
    if [ "$status" -eq 130 ] || [ "$status" -eq 143 ]; then
      printf '\nINTERRUPTED: %s\n' "$name"
      exit "$status"
    fi
    FAILED_STEPS+=("$name")
    printf '\nFAIL: %s (exit code %s)\n' "$name" "$status"
  fi
}

run_python_tests() {
  local name="$1"
  local pythonpath="$2"
  local test_dir="$3"
  shift 3

  run_step "$name" env \
    "UV_CACHE_DIR=$UV_CACHE_DIR" \
    "PYTHONPATH=$pythonpath" \
    uv run --python "$PYTHON_VERSION" --no-project "$@" \
    python -B -m unittest discover -s "$test_dir"
}

print_summary() {
  printf '\n'
  printf '========================================================================\n'
  printf 'TEST SUMMARY\n'
  printf '========================================================================\n'
  printf 'Passed steps: %s\n' "${#PASSED_STEPS[@]}"
  for step in "${PASSED_STEPS[@]}"; do
    printf '  PASS %s\n' "$step"
  done

  printf 'Failed steps: %s\n' "${#FAILED_STEPS[@]}"
  for step in "${FAILED_STEPS[@]}"; do
    printf '  FAIL %s\n' "$step"
  done

  if [ "${#FAILED_STEPS[@]}" -eq 0 ]; then
    printf '\nALL TEST STEPS PASSED\n'
  else
    printf '\nSOME TEST STEPS FAILED\n'
  fi
}

cd "$ROOT_DIR" || exit 1

run_python_tests \
  "analysis-module unit tests" \
  "$ROOT_DIR/analysis-module/src:$ROOT_DIR/analysis-module/tests" \
  "analysis-module/tests" \
  --with joblib \
  --with scikit-learn

run_python_tests \
  "analysis-service unit/api tests" \
  "$ROOT_DIR/analysis-service/src:$ROOT_DIR/analysis-module/src:$ROOT_DIR/telemetry-converter/src:$ROOT_DIR/telemetry-source/backend/src" \
  "analysis-service/tests" \
  --with fastapi \
  --with httpx

run_python_tests \
  "telemetry-converter unit tests" \
  "$ROOT_DIR/telemetry-converter/src" \
  "telemetry-converter/tests"

run_python_tests \
  "telemetry-source backend unit/api tests" \
  "$ROOT_DIR/telemetry-source/backend/src:$ROOT_DIR/telemetry-converter/src" \
  "telemetry-source/backend/tests" \
  --with fastapi \
  --with httpx

run_step \
  "telemetry-source frontend unit tests" \
  docker run --rm \
    -v "$ROOT_DIR:/work" \
    -w /work/telemetry-source/frontend \
    "$NODE_IMAGE" \
    sh -lc "npm ci && npm test"

run_step \
  "telemetry-viewer frontend build" \
  docker run --rm \
    -v "$ROOT_DIR:/work" \
    -w /work/telemetry-viewer/frontend \
    "$NODE_IMAGE" \
    sh -lc "npm ci && npm run build"

run_step \
  "docker compose stack" \
  docker compose up --build -d --wait

run_step \
  "end-to-end tests" \
  docker run --rm \
    --network "$COMPOSE_NETWORK" \
    --ipc=host \
    -v "$ROOT_DIR:/work" \
    -v telemetry-e2e-node-modules:/work/e2e-tests/node_modules \
    -w /work/e2e-tests \
    -e E2E_ANALYSIS_BASE_URL=http://analysis-service:8010 \
    -e E2E_TELEMETRY_SOURCE_BASE_URL=http://telemetry-source-backend:8000 \
    -e E2E_VIEWER_BASE_URL=http://telemetry-viewer \
    -e E2E_STREAM_TARGET_HOST=analysis-service \
    "$PLAYWRIGHT_IMAGE" \
    sh -lc "npm ci && npm test"

print_summary

if [ "${#FAILED_STEPS[@]}" -eq 0 ]; then
  exit 0
fi
exit 1
