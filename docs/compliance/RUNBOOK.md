# Compliance Runbook

This runbook is the operational entry point for running and maintaining the compliance-grade deterministic release system.

It is designed for an engineer encountering the repository for the first time.

## Local development quickstart (IdP stub + dev signer)

### Start stack

```bash
docker compose -f deploy/reference/docker-compose.yml up --build -d
```

### Run migrations (if using local DB outside compose)

```bash
make migrate
```

### Run compliance gate + smoke

```bash
make compliance-gate
make compliance-smoke
```

Outputs:
- `evidence/` directory from smoke (report JSON, downloaded bundles, verification reports)

## Release signing flow (production posture)

Tagged releases (`v*`) are signed in CI using AWS KMS via GitHub OIDC.

Prerequisites:
- AWS OIDC role configured
- Secrets set (see `docs/compliance/RELEASE_READINESS.md`)
- Revocation feed published (for procurement gate)

Release assets are published to the GitHub Release object:
- `release.zip`
- `RELEASE_MANIFEST.json`
- `RELEASE_ATTESTATION.json`
- `RELEASE_PUBLIC_KEYS.json`
- `release-verifier.zip`
- `release-verifier.sha256`
- `release-verifier.attestation.json`
- `SBOM.cdx.json`, `SBOM.spdx.json`
- `PROVENANCE.json`, `PROVENANCE_ATTESTATION.json`
- `KEY_REVOCATIONS.json`
- `REVOCATION_AUTHORITY_PUBLIC_KEYS.json`

## Publishing the revocation feed

Use:

- `.github/workflows/publish-revocations.yml` (workflow_dispatch)

This publishes:
- `REVOCATION_FEED.json`
- `KEY_REVOCATIONS.json`
- `REVOCATION_AUTHORITY_PUBLIC_KEYS.json`

to `gh-pages` by default.

## Revocation event flow (key compromise)

1) Add compromised `kid` to `KEY_REVOCATIONS.json` (under revocation authority signing).
2) Publish updated revocation feed.
3) Procurement verification must reject releases signed by revoked `kid`.

## External verification (auditor)

Use `release-verifier.zip`:
- verify verifier bundle (sha256 + attestation)
- run `audit_verify.py` against extracted release

See `tools/release-verifier/EXTERNAL_AUDIT.md`.

## “First 30 minutes” checklist

1) Start stack: `docker compose up -d`
2) Gate: `make compliance-gate`
3) Smoke: `make compliance-smoke`
4) Inspect: `ui/artifact-browser` (optional) or `evidence/` output
5) Run demo: `scripts/demo_golden_path.sh`
