# Static Analysis

This directory contains the reproducible static analysis and dependency audit
tooling for the repository. It is intentionally kept outside runtime modules:
the security value is in the analyzers and their configuration, not in a build
or task wrapper.

## Scope

- Python quality checks: `ruff`, `mypy`
- Python security checks: `bandit`, `pip-audit`
- Frontend quality checks: `tsc`, `eslint`
- Frontend dependency audit: `npm audit`
- Secret scanning: `gitleaks`

The Bandit profile excludes:

- `B101`: unit tests use assertions.
- `B104`: listener bind addresses are runtime configuration for telemetry input.
- `B311`: synthetic telemetry noise uses pseudo-random values outside
  cryptographic contexts.

## Docker Usage

Build the analysis image:

```powershell
docker compose -f tools/static-analysis/compose.yaml build
```

Run all checks:

```powershell
docker compose -f tools/static-analysis/compose.yaml run --rm static-analysis ./tools/static-analysis/scripts/run-all.sh
```

Run only quality checks:

```powershell
docker compose -f tools/static-analysis/compose.yaml run --rm static-analysis ./tools/static-analysis/scripts/quality-check.sh
```

Run only security checks:

```powershell
docker compose -f tools/static-analysis/compose.yaml run --rm static-analysis ./tools/static-analysis/scripts/security-check.sh
```

`pip-audit`, `npm audit`, the Docker image build, and `gitleaks` installation
require network access.
