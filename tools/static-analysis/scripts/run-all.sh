#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

bash tools/static-analysis/scripts/quality-check.sh
bash tools/static-analysis/scripts/security-check.sh
