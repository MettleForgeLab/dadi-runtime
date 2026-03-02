# Compliance Gate

The compliance gate is a strict readiness check intended for CI and deployment pipelines.

## Endpoint

- `GET /health/compliance?strict=true`

Returns:
- `ok: true|false`
- `failures: [...]` with machine-readable failure codes

## Script

- `scripts/compliance_gate.py` calls the endpoint and exits non-zero on failure.

## Makefile

- `make compliance-gate`

Use this as a deployment preflight check.
