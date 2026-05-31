#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

bandit -c tools/static-analysis/configs/bandit.yaml -r \
  analysis-module/src \
  analysis-service/src \
  telemetry-converter/src \
  telemetry-source/backend/src

pip-audit -r tools/static-analysis/configs/python-audit-requirements.txt
npm audit --prefix telemetry-viewer/frontend
gitleaks detect \
  --source . \
  --config tools/static-analysis/configs/gitleaks.toml \
  --no-banner
