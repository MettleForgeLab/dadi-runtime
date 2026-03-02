# Changelog

## v0.2.1-compliance — 2026-02-28

### Revocation distribution and freshness
- Signed `REVOCATION_FEED.json` generation and publishing workflow
- Verifier support for optional feed fetching with fail-closed options
- Verification profiles: `archival` (offline) and `procurement` (fresh feed required)
- Procurement-mode release gate using `REVOCATION_FEED_URL` (GitHub Pages recommended)

### Verifier usability and integrity
- Self-contained `audit_verify.py` verifier
- Verifier bundle launcher scripts (`run.sh`, `run.ps1`) and `EXTERNAL_AUDIT.md`
- Verifier bundle SHA256 + signed asset attestation

### Operations
- `docs/compliance/RUNBOOK.md` and `docs/compliance/ASSET_INDEX.md`
- `make bootstrap` and golden-path demo script

## v0.2.0-compliance — 2026-02-28

This release consolidates the compliance-grade deterministic artifact stack into a single versioned snapshot.

### Identity and tenant isolation
- OIDC/JWKS authentication mode (production posture)
- Tenant isolation via token-derived tenant_id + Postgres RLS expectations

### Release objects and export policy
- Deliverables lifecycle: draft → final → sent
- Bundle generation with signed, schema-validated manifests
- Evidence packets with signed, schema-validated evidence manifests
- Sent-only export for bundles and evidence with dedicated scopes
- Revocation and retention mechanisms
- Download receipts recorded in tamper-evident audit log

### Integrity and auditability
- Hash-chained audit events and chain verification endpoint
- Closure verification and diagnostics for bundle completeness
- Adversarial tamper tests and cross-tenant boundary tests

### Operational hardening
- Streaming responses for byte-heavy endpoints
- Distributed rate limiting option (Redis backend) and request size limits
- Compliance health endpoint and strict compliance gate script
- CI workflows:
  - compliance gate
  - migrations

### Migration discipline
- Alembic migrations with baseline revision
- SQL checksum enforcement for baseline inputs in prod mode
- Schema contract test and migrations CI workflow

### Notes
- Dev simulation includes an IdP stub and dev signer; production posture requires real IdP and KMS.
