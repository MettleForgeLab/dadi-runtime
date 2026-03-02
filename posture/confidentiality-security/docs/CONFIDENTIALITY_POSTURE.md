# Confidentiality Posture (Operational)

This document describes confidentiality rules for a financial-services document analysis system built on deterministic artifacts.

## Principles

- Artifact bytes may contain confidential client data.
- Debugging surfaces are a primary leakage vector.
- Determinism is not security. Reproducibility does not imply safety.

## API Controls

### Deny-by-default for content bytes

Endpoints that return artifact bytes (e.g., `GET /artifacts/{sha256}/content`) must be treated as high risk.

Policy requirements:
- Authentication required.
- Explicit opt-in header required (`X-DADI-Allow-Content: true` by default).
- Prefer returning metadata by default, not bytes.

### No content in logs

- Never log request bodies.
- Never log response bodies.
- Redact Authorization and Cookie headers.
- Treat error messages as potentially sensitive; do not include payload excerpts.

## Export Controls

### Regression fixtures

Two modes:
- Manifest-only export (allowed): hashes, sizes, boundaries, drift localization data.
- Bytes export (default denied): raw artifact bytes should not leave the enclave without explicit approval.

## Storage posture

- Postgres-only is acceptable for MVP in a sealed environment.
- For scale: blob store + Postgres pointers.
- Encryption at rest is delegated to infrastructure controls (managed Postgres, encrypted volumes, KMS-backed blob stores).

## Threat boundaries (explicit non-claims)

- Determinism boundary is defined relative to a declared toolchain and invocation parameters.
- Hash identity binds bytes, not truth.
- Deterministic replay does not validate correctness.
- This posture does not replace:
  - identity management systems
  - network security
  - upstream data integrity checks
