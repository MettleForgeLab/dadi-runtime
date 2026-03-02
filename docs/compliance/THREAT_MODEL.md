# Threat Model

This document freezes the security and integrity assumptions for the compliance-grade deployment profile.

It exists to:
- make trust boundaries explicit,
- define what the system guarantees,
- define what the system does not guarantee,
- prevent silent erosion of invariants over time.

## System summary

The system maintains:
- immutable, hash-identified artifacts,
- deterministic execution boundaries for structured outputs,
- tenant isolation enforced by JWT/OIDC tenant claims plus Postgres RLS,
- signed bundle and evidence manifests,
- export controls (sent-only + scope-gated),
- tamper-evident audit logging (hash-chained audit events),
- policy enforcement tests and a strict compliance gate.

## Assets

Primary assets protected by this system:

- **Artifact bytes**: canonical JSON artifacts, rendered deliverables (DOCX), bundles/evidence ZIPs.
- **Artifact identity**: SHA256 digests and lineage edges.
- **Tenant boundary**: the separation between tenant datasets.
- **Release objects**: deliverables, bundles, evidence packets.
- **Signing trust root**: signing provider keys (AWS KMS in production).
- **Audit log integrity**: hash-chained audit events and chain verification.
- **Authorization policy**: scope requirements and lifecycle gates.

## Trust boundaries

### External client → Gateway API

Trust assumptions:
- Tokens are validated (OIDC/JWKS in prod; dev stub in local simulation).
- Request is untrusted until auth middleware sets tenant context.

Controls:
- Authentication middleware sets `request.state.tenant_id` (from token claim).
- Scope enforcement for high-risk endpoints (export/download, bytes endpoints).
- Rate limiting and request size limits.
- Fail-closed schema validation at critical boundaries.

### Gateway → Database

Trust assumptions:
- Postgres enforces RLS correctly when enabled.
- Gateway sets tenant context consistently for every connection/transaction.

Controls:
- `SET app.tenant_id = <tenant>` applied to connections/transactions.
- RLS policies prevent cross-tenant reads/writes.
- Audit chain and policy enforcement checks are stored server-side.

### Gateway → Signing Provider

Trust assumptions:
- In production, AWS KMS (or equivalent) protects private key material.
- In dev, in-memory signing is allowed only under `DADI_ENV=dev`.

Controls:
- Prod posture requires `DADI_SIGNING_PROVIDER=aws_kms` and OIDC auth.
- Signatures include `(alg, kid, sig, key_ref)` envelope.
- Public key caching and ledger support historical verification.
- Health checks validate signing readiness.

### Offline verification boundary

Trust assumptions:
- Verifier has access to the appropriate public keys (or KMS-derived keys).
- Offline verification does not trust the gateway for correctness of bundle contents.

Controls:
- ZIP integrity: each `artifacts/<sha>` entry hashes to `<sha>`.
- Manifest signature verification.
- Optional closure verification against gateway endpoints if desired.

## In-scope threats and mitigations

### Cross-tenant access
Threat: tenant B reads tenant A metadata or bytes.

Mitigations:
- Tenant derived from token claim.
- RLS enforces tenant boundary at DB.
- Cross-tenant adversarial tests.

### Artifact mutation and silent drift
Threat: artifact bytes change without traceability.

Mitigations:
- Immutable artifact model; SHA256 identity.
- Fail-closed stage boundaries and schema validation.
- Run diff engine and closure verification.

### Bundle/evidence tampering
Threat: attacker modifies manifest or bundle bytes post-creation.

Mitigations:
- Signed manifests.
- Schema validation (fail-closed).
- ZIP integrity checks.
- Closure_mode verification (stage_runs_v1) and diagnostics.
- Tamper adversarial tests.

### Unauthorized export
Threat: user downloads deliverable bundles/evidence without proper authorization.

Mitigations:
- Sent-only export policy.
- Dedicated download endpoints with dedicated scopes:
  - `deliverable:download_bundle`
  - `deliverable:evidence_download`
- Generic `/artifacts/{sha}/content` blocks bundle/evidence zip by type.
- Revocation support denies downloads after revoke.

### Replay / duplicate mutations
Threat: retries or concurrent requests create duplicate or inconsistent release objects.

Mitigations:
- Idempotency keys for mutation endpoints.
- DB uniqueness constraints where appropriate.
- Concurrency tests.

### Audit log repudiation
Threat: actor disputes whether a bundle was downloaded or a deliverable was finalized.

Mitigations:
- Audit events for lifecycle transitions and download receipts.
- Hash-chained audit log and verify-chain endpoint.
- Compliance evidence bundles can include audit excerpts and chain verification.

### Denial of service
Threat: repeated or oversized requests degrade service.

Mitigations:
- Request size limits.
- Rate limiting (Redis-backed for multi-instance).
- Streaming responses for large byte surfaces.

## Out-of-scope threats and non-goals

These are explicitly not solved by the system:

- Upstream data correctness, truthfulness, or semantic validity of inputs/outputs.
- Client-side exfiltration after a user downloads an authorized export.
- Full network perimeter security (TLS termination, WAF, firewalling), assumed external.
- Insider with DB superuser privileges bypassing RLS (can be mitigated operationally).
- Compromise of signing provider (e.g., KMS key compromise) beyond operational key management.
- General AI safety, hallucination elimination, alignment, or model behavior guarantees.

## Frozen invariants

These invariants must not change without explicit versioning and documented justification:

1. **Artifacts are immutable and hash-identified.**
2. **Bundles and evidence manifests are signed and schema-validated.**
3. **Export is sent-only and scope-gated through dedicated endpoints.**
4. **Revoked bundles/evidence cannot be downloaded.**
5. **Audit events are hash-chained and verifiable.**
6. **Tenant boundary is enforced by token-derived tenant_id + RLS.**
7. **Fail-closed validation at declared boundaries.**

## Enforcement map

Where invariants are enforced:

- Auth/scopes: auth middleware + endpoint checks.
- Tenant isolation: DB RLS + `SET app.tenant_id` in DB helpers.
- Signing: signing provider (`aws_kms` in prod) + signature envelope.
- Manifest schema: schema validators for deliverable/evidence manifests.
- Closure verification: `/bundle/verify` closure checks.
- Export policy: sent-only checks and scope-gated download endpoints.
- Revocation: status checks in download endpoints + revocation endpoints.
- Audit chain: audit emit function + `/audit/verify-chain`.
- Compliance posture: `/health/compliance?strict=true` and gate script.

## Change control

Any change to:
- scopes,
- download endpoints,
- signing provider behavior,
- schema versions,
- closure modes,
- audit hashing,
must update:
- this document,
- `docs/compliance/AUTHZ_MATRIX.md`,
- compliance gate expectations,
and must include new or updated tests.
