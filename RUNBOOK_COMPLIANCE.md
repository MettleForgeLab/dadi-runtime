# Compliance Dev Loop (Local)

This runbook describes the local compliance simulation environment:

- Postgres
- Gateway (OIDC mode)
- Local IdP stub (JWKS + token issuer)
- UI

## Start

```bash
make compliance-up
```

## Get token (tenant_a)

```bash
make token TENANT=tenant_a SCOPE="artifact:read_bytes deliverable:download_bundle"
```

Set UI token:

```bash
export NEXT_PUBLIC_AUTH_TOKEN="<token>"
```

## Seed demo data

```bash
make compliance-seed
```

This writes `.seed_state.json` at repo root.

## Run compliance smoke

```bash
make compliance-smoke
```

Outputs:
- `smoke_report.json`
- `bundle_downloaded.zip` (if created)
- `bundle_verification_report.json` (if created)

## Shut down

```bash
make compliance-down
```


## Evidence output

Smoke run writes artifacts into `evidence/`:
- `smoke_report.json`
- `bundle_downloaded.zip`
- `bundle_verification_report.json`
- `audit_excerpt.json`
- `metrics_excerpt.json`
